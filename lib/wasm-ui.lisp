;; -*- mode: lisp; package: ccl.wasm-ui -*-
;; Minimal Lisp-side UI bridge support for WASM bring-up.

(defpackage :ccl.wasm-ui
  (:use :cl)
  (:export
   :make-ui-state
   :ui-state
   :ui-task
   :ui-window
   :ui-widget
   :ui-command
   :ui-add-task
   :ui-add-window
   :ui-add-widget
   :ui-register-command
   :ui-get-task
   :ui-get-window
   :ui-get-widget
   :ui-get-command
   :ui-set-widget-text
   :ui-set-focus
   :ui-enqueue-event
   :ui-enqueue-signal
   :ui-poll-and-enqueue
   :ui-handle-event
   :ui-handle-signal
   :ui-build-tree
   :ui-run-turn
   :ui-demo-state
   :ui-demo-turn
   :ui-node
   :ui-text
   :ui-element
   :ui-encode-tree
   :ui-decode-events
   :ui-render-tree
   :ui-poll-events
   :ui-measure-text
   :ui-example-tree))

(in-package :ccl.wasm-ui)

(defconstant +ui-tree-magic+ #x55494231)  ; "UIB1"
(defconstant +ui-event-magic+ #x55494531) ; "UIE1"
(defconstant +ui-proto-version+ 1)

(defconstant +ui-kind-text+ 0)
(defconstant +ui-kind-element+ 1)

(defconstant +ui-value-null+ 0)
(defconstant +ui-value-bool+ 1)
(defconstant +ui-value-number+ 2)
(defconstant +ui-value-string+ 3)

(defconstant +ui-null-index+ #xffffffff)

(defconstant +ui-event-pointer+ 1)
(defconstant +ui-event-key+ 2)
(defconstant +ui-event-composition+ 3)
(defconstant +ui-event-text+ 4)
(defconstant +ui-event-focus+ 5)
(defconstant +ui-event-blur+ 6)
(defconstant +ui-event-wheel+ 7)

(defconstant +ui-pointer-flag-down+ 1)
(defconstant +ui-pointer-flag-up+ 2)
(defconstant +ui-pointer-flag-move+ 4)
(defconstant +ui-pointer-flag-enter+ 8)
(defconstant +ui-pointer-flag-leave+ 16)
(defconstant +ui-pointer-flag-cancel+ 32)

(defconstant +ui-key-flag-down+ 1)
(defconstant +ui-key-flag-up+ 2)

(defstruct ui-node
  kind
  tag
  props
  children
  text
  key)

(defun ui-text (text &key key)
  (make-ui-node :kind :text :text (string text) :key key))

(defun %normalize-props (props)
  (cond ((null props) nil)
        ((and (listp props) (every #'consp props))
         (let ((sorted (sort (copy-list props)
                             #'string<
                             :key (lambda (entry)
                                    (let ((k (car entry)))
                                      (if (stringp k)
                                          k
                                          (error "UI prop keys must be strings: ~S" k)))))))
           (mapcar (lambda (entry)
                     (cons (car entry) (cdr entry)))
                   sorted)))
        (t (error "UI props must be an alist of string keys"))))

(defun %normalize-children (children)
  (let ((out nil))
    (labels ((push-child (child)
               (cond ((null child) nil)
                     ((typep child 'ui-node)
                      (push child out))
                     ((listp child)
                      (dolist (item child) (push-child item)))
                     ((or (stringp child) (numberp child))
                      (push (ui-text child) out))
                     (t (error "Unsupported child type: ~S" child)))))
      (push-child children))
    (nreverse out)))

(defun ui-element (tag props children &key key)
  (make-ui-node :kind :element
                :tag (string tag)
                :props (%normalize-props props)
                :children (%normalize-children children)
                :key key))

(defun %string->octets (s)
  (let* ((text (string s))
         (len (length text))
         (out (make-array len :element-type '(unsigned-byte 8))))
    (dotimes (i len out)
      (setf (aref out i) (char-code (char text i))))))

(defun %write-u32 (vec offset value)
  (let ((v (logand value #xffffffff)))
    (setf (aref vec offset) (ldb (byte 8 0) v)
          (aref vec (+ offset 1)) (ldb (byte 8 8) v)
          (aref vec (+ offset 2)) (ldb (byte 8 16) v)
          (aref vec (+ offset 3)) (ldb (byte 8 24) v))
    (+ offset 4)))

(defun %write-f64 (vec offset value)
  (multiple-value-bind (hi lo) (ccl::double-float-bits (coerce value 'double-float))
    (let ((off (%write-u32 vec offset lo)))
      (%write-u32 vec off hi))))

(defun %read-u32 (vec offset)
  (logior (aref vec offset)
          (ash (aref vec (+ offset 1)) 8)
          (ash (aref vec (+ offset 2)) 16)
          (ash (aref vec (+ offset 3)) 24)))

(defun %read-f64 (vec offset)
  (let ((lo (%read-u32 vec offset))
        (hi (%read-u32 vec (+ offset 4))))
    (ccl::double-float-from-bits hi lo)))

(defstruct (string-table (:constructor make-string-table))
  map
  strings
  bytes
  total-size)

(defun %make-string-table ()
  (make-string-table :map (make-hash-table :test 'equal)
                     :strings (make-array 0 :adjustable t :fill-pointer 0)
                     :bytes (make-array 0 :adjustable t :fill-pointer 0)
                     :total-size 0))

(defun %string-index (table value)
  (if (null value)
      +ui-null-index+
      (let* ((s (string value))
             (existing (gethash s (string-table-map table))))
        (if existing
            existing
            (let* ((idx (fill-pointer (string-table-strings table)))
                   (bytes (%string->octets s)))
              (setf (gethash s (string-table-map table)) idx)
              (vector-push-extend s (string-table-strings table))
              (vector-push-extend bytes (string-table-bytes table))
              (incf (string-table-total-size table) (+ 4 (length bytes)))
              idx)))))

(defun %encode-prop (table key value)
  (let ((key-index (%string-index table key)))
    (cond ((null value)
           (list key-index +ui-value-null+ 0 0))
          ((or (eq value t) (eq value nil))
           (list key-index +ui-value-bool+ (if value 1 0) 0))
          ((numberp value)
           (multiple-value-bind (hi lo) (ccl::double-float-bits (coerce value 'double-float))
             (list key-index +ui-value-number+ lo hi)))
          ((stringp value)
           (list key-index +ui-value-string+ (%string-index table value) 0))
          (t (error "Unsupported prop value: ~S" value)))))

(defun %encode-node (node table nodes)
  (let* ((index (fill-pointer nodes)))
    (vector-push-extend nil nodes)
    (ecase (ui-node-kind node)
      (:text
       (let ((text-index (%string-index table (ui-node-text node)))
             (key-index (%string-index table (ui-node-key node))))
         (setf (aref nodes index)
               (list :kind +ui-kind-text+
                     :key-index key-index
                     :text-index text-index))))
      (:element
       (let* ((tag-index (%string-index table (ui-node-tag node)))
              (key-index (%string-index table (ui-node-key node)))
              (props (ui-node-props node))
              (children (ui-node-children node))
              (prop-enc (mapcar (lambda (entry)
                                  (%encode-prop table (car entry) (cdr entry)))
                                props))
              (child-indices (mapcar (lambda (child)
                                       (%encode-node child table nodes))
                                     children)))
         (setf (aref nodes index)
               (list :kind +ui-kind-element+
                     :key-index key-index
                     :tag-index tag-index
                     :props prop-enc
                     :children child-indices)))))
    index))

(defun ui-encode-tree (node)
  (let* ((table (%make-string-table))
         (nodes (make-array 0 :adjustable t :fill-pointer 0))
         (root-index (%encode-node node table nodes))
         (string-count (fill-pointer (string-table-strings table)))
         (node-count (fill-pointer nodes))
         (string-table-size (string-table-total-size table))
         (node-size 0))
    (dotimes (i node-count)
      (let* ((entry (aref nodes i))
             (kind (getf entry :kind)))
        (incf node-size 12)
        (if (= kind +ui-kind-text+)
            (incf node-size 4)
            (let* ((props (getf entry :props))
                   (children (getf entry :children)))
              (incf node-size 12)
              (incf node-size (* 16 (length props)))
              (incf node-size (* 4 (length children)))))))
    (let* ((total-size (+ 24 string-table-size node-size))
           (out (make-array total-size :element-type '(unsigned-byte 8)))
           (offset 0))
      (setf offset (%write-u32 out offset +ui-tree-magic+))
      (setf offset (%write-u32 out offset +ui-proto-version+))
      (setf offset (%write-u32 out offset string-count))
      (setf offset (%write-u32 out offset node-count))
      (setf offset (%write-u32 out offset root-index))
      (setf offset (%write-u32 out offset 0))
      (dotimes (i string-count)
        (let* ((bytes (aref (string-table-bytes table) i))
               (len (length bytes)))
          (setf offset (%write-u32 out offset len))
          (dotimes (j len)
            (setf (aref out offset) (aref bytes j))
            (incf offset))))
      (dotimes (i node-count)
        (let* ((entry (aref nodes i))
               (kind (getf entry :kind))
               (key-index (getf entry :key-index))
               (flags (if (and key-index (/= key-index +ui-null-index+)) 1 0)))
          (setf offset (%write-u32 out offset kind))
          (setf offset (%write-u32 out offset flags))
          (setf offset (%write-u32 out offset (or key-index +ui-null-index+)))
          (if (= kind +ui-kind-text+)
              (setf offset (%write-u32 out offset (getf entry :text-index)))
              (let* ((props (getf entry :props))
                     (children (getf entry :children)))
                (setf offset (%write-u32 out offset (getf entry :tag-index)))
                (setf offset (%write-u32 out offset (length props)))
                (setf offset (%write-u32 out offset (length children)))
                (dolist (prop props)
                  (setf offset (%write-u32 out offset (first prop)))
                  (setf offset (%write-u32 out offset (second prop)))
                  (setf offset (%write-u32 out offset (third prop)))
                  (setf offset (%write-u32 out offset (fourth prop))))
                (dolist (child-index children)
                  (setf offset (%write-u32 out offset child-index)))))))
      out)))

(defun ui-decode-events (payload)
  (unless (and payload (typep payload '(simple-array (unsigned-byte 8) (*))))
    (error "UI event payload must be a (simple-array (unsigned-byte 8) (*))"))
  (let* ((magic (%read-u32 payload 0))
         (version (%read-u32 payload 4)))
    (unless (and (= magic +ui-event-magic+) (= version +ui-proto-version+))
      (error "Unsupported UI event payload"))
    (let* ((string-count (%read-u32 payload 8))
           (event-count (%read-u32 payload 12))
           (offset 16)
           (strings (make-array string-count)))
      (dotimes (i string-count)
        (let* ((len (%read-u32 payload offset)))
          (incf offset 4)
          (let ((buf (make-array len :element-type '(unsigned-byte 8))))
            (dotimes (j len)
              (setf (aref buf j) (aref payload (+ offset j))))
            (setf (aref strings i) (map 'string #'code-char buf)))
          (incf offset len)))
      (labels ((str (idx)
                 (if (= idx +ui-null-index+)
                     nil
                     (aref strings idx))))
        (let ((events nil))
          (dotimes (_ event-count)
            (let* ((etype (%read-u32 payload offset))
                   (flags (%read-u32 payload (+ offset 4)))
                   (target (str (%read-u32 payload (+ offset 8))))
                   (window (str (%read-u32 payload (+ offset 12)))))
              (incf offset 16)
              (let ((event (list :type etype :flags flags :target-id target :window-id window)))
                (cond
                  ((= etype +ui-event-pointer+)
                   (setf event
                         (list* :x (%read-f64 payload offset)
                                :y (%read-f64 payload (+ offset 8))
                                :button (ldb (byte 32 0) (%read-u32 payload (+ offset 16)))
                                :buttons (ldb (byte 32 0) (%read-u32 payload (+ offset 20)))
                                :modifiers (%read-u32 payload (+ offset 24))
                                :pointer-type (%read-u32 payload (+ offset 28))
                                :click-count (%read-u32 payload (+ offset 32))
                                event))
                   (incf offset 40))
                  ((= etype +ui-event-key+)
                   (setf event
                         (list* :key (str (%read-u32 payload offset))
                                :code (str (%read-u32 payload (+ offset 4)))
                                :modifiers (%read-u32 payload (+ offset 8))
                                :repeat (%read-u32 payload (+ offset 12))
                                :location (%read-u32 payload (+ offset 16))
                                :is-composing (%read-u32 payload (+ offset 20))
                                :text (str (%read-u32 payload (+ offset 24)))
                                event))
                   (incf offset 32))
                  ((= etype +ui-event-composition+)
                   (setf event
                         (list* :phase (%read-u32 payload offset)
                                :data (str (%read-u32 payload (+ offset 4)))
                                event))
                   (incf offset 16))
                  ((= etype +ui-event-text+)
                   (setf event
                         (list* :text (str (%read-u32 payload offset)) event))
                   (incf offset 16))
                  ((or (= etype +ui-event-focus+) (= etype +ui-event-blur+))
                   (setf event
                         (list* :related-id (str (%read-u32 payload offset)) event))
                   (incf offset 16))
                  ((= etype +ui-event-wheel+)
                   (setf event
                         (list* :delta-x (%read-f64 payload offset)
                                :delta-y (%read-f64 payload (+ offset 8))
                                :delta-mode (%read-u32 payload (+ offset 16))
                                :modifiers (%read-u32 payload (+ offset 20))
                                event))
                   (incf offset 32))
                  (t
                   (incf offset 16)))
                (push event events))))
          (nreverse events))))))

(defun ui-render-tree (node-or-bytes)
  (let* ((bytes (if (typep node-or-bytes 'ui-node)
                    (ui-encode-tree node-or-bytes)
                    node-or-bytes)))
    (ccl:with-pointer-to-ivector (ptr bytes)
      (ccl:external-call "wasm_kernel_ui_render"
                     :address ptr
                     :unsigned-long (length bytes)
                     :signed-long))))

(defun ui-poll-events (&key (max-events 64) (max-bytes 65536) (allow-pending t))
  (let* ((buffer (make-array max-bytes :element-type '(unsigned-byte 8)))
         (flags (if allow-pending 1 0)))
    (ccl:rlet ((out-len :unsigned-long)
               (out-count :unsigned-long))
      (let ((r (ccl:with-pointer-to-ivector (ptr buffer)
                 (ccl:external-call "wasm_kernel_ui_poll"
                                :unsigned-long max-events
                                :unsigned-long max-bytes
                                :unsigned-long flags
                                :address ptr
                                :unsigned-long max-bytes
                                :address out-len
                                :address out-count
                                :signed-long))))
        (cond ((< r 0) (values nil r))
              (t
               (let* ((n (ccl:pref out-len :unsigned-long))
                      (bytes (if (and n (> n 0))
                                 (let ((copy (make-array n :element-type '(unsigned-byte 8))))
                                   (replace copy buffer :end2 n)
                                   copy)
                                 (make-array 0 :element-type '(unsigned-byte 8))))
                      (events (if (> (length bytes) 0)
                                  (ui-decode-events bytes)
                                  nil)))
                 (values events r))))))))

(defun ui-measure-text (font text)
  (let* ((font-bytes (%string->octets (or font "")))
         (text-bytes (%string->octets (or text ""))))
    (ccl:with-pointer-to-ivector (font-ptr font-bytes)
      (ccl:with-pointer-to-ivector (text-ptr text-bytes)
        (ccl:rlet ((metrics :double-float 4))
          (let ((r (ccl:external-call "wasm_kernel_ui_measure_text"
                                  :address font-ptr
                                  :unsigned-long (length font-bytes)
                                  :address text-ptr
                                  :unsigned-long (length text-bytes)
                                  :address metrics
                                  :signed-long)))
            (if (< r 0)
                (values nil r)
                (values (list :width (ccl:paref metrics :double-float 0)
                              :height (ccl:paref metrics :double-float 1)
                              :ascent (ccl:paref metrics :double-float 2)
                              :descent (ccl:paref metrics :double-float 3))
                        0))))))))

(defun %ui-eagain-p (value)
  (let ((eagain (symbol-value (read-from-string "#$EAGAIN"))))
    (eql value (- eagain))))

(defun %ui-maybe-yield-on-pending (state result allow-pending)
  (declare (ignorable state result allow-pending))
  #+wasm32-target
  (when (and allow-pending (numberp result) (%ui-eagain-p result))
    (setf (ui-state-yield-reason state) "ui-poll-pending")
    (when (fboundp 'ccl::wasm-yield-ui-turn)
      (ccl::wasm-yield-ui-turn "ui-poll-pending"))
    (when (and (boundp 'ccl::*wasm-yield-on-eagain*)
               ccl::*wasm-yield-on-eagain*)
      (throw :wasm-yield (list :ui "poll" :reason "pending")))))

(defun ui-example-tree ()
  (ui-element "div"
              '(("className" . "root")
                ("data-widget-id" . "root-1"))
              (list
               (ui-element "button"
                           '(("data-widget-id" . "btn-1")
                             ("data-command-id" . "demo.click"))
                           (list (ui-text "Click")))
               (ui-element "div"
                           '(("data-widget-id" . "label-1"))
                           (list (ui-text "Ready"))))))

;;;; ------------------------------------------------------------
;;;; Minimal Lisp UI core (Phase 5 MVP)
;;;; ------------------------------------------------------------

(defstruct ui-command
  id
  doc
  enabled-p
  handler)

(defstruct ui-widget
  id
  kind
  props
  children
  command-id
  text
  state)

(defstruct ui-window
  id
  title
  root-widget-id
  task-id)

(defstruct ui-task
  id
  label
  window-ids
  active-window-id)

(defstruct (ui-state (:constructor make-ui-state (&key)))
  (tasks (make-hash-table :test 'equal))
  (task-order nil)
  (windows (make-hash-table :test 'equal))
  (window-order nil)
  (widgets (make-hash-table :test 'equal))
  (widget-order nil)
  (commands (make-hash-table :test 'equal))
  (command-order nil)
  (focus-widget-id nil)
  (signal-queue nil)
  (event-queue nil)
  (turn-phase :idle)
  (yield-reason nil)
  (next-task-id 1)
  (next-window-id 1)
  (next-widget-id 1))

(defparameter *ui-snapshot-version* 1)
(defparameter *ui-persist-path* "/ui/wasm-ui-state.lisp")

(defun %copy-list-safe (value)
  (if (listp value) (copy-list value) value))

(defun %hash-values (table)
  (let (out)
    (maphash (lambda (_k v)
               (declare (ignore _k))
               (push v out))
             table)
    (nreverse out)))

(defun %ordered-values (order table)
  (let ((out nil))
    (dolist (key order)
      (let ((value (gethash key table)))
        (when value
          (push value out))))
    (nreverse out)))

(defun %snapshot-task (task)
  (list :id (ui-task-id task)
        :label (ui-task-label task)
        :window-ids (%copy-list-safe (ui-task-window-ids task))
        :active-window-id (ui-task-active-window-id task)))

(defun %snapshot-window (window)
  (list :id (ui-window-id window)
        :title (ui-window-title window)
        :root-widget-id (ui-window-root-widget-id window)
        :task-id (ui-window-task-id window)))

(defun %snapshot-widget (widget)
  (list :id (ui-widget-id widget)
        :kind (ui-widget-kind widget)
        :props (%copy-list-safe (ui-widget-props widget))
        :children (%copy-list-safe (ui-widget-children widget))
        :command-id (ui-widget-command-id widget)
        :text (ui-widget-text widget)
        :state (ui-widget-state widget)))

(defun %snapshot-command (command)
  (list :id (ui-command-id command)
        :doc (ui-command-doc command)))

(defun ui-state->snapshot (state &key (include-commands t))
  (let* ((task-order (%copy-list-safe (ui-state-task-order state)))
         (window-order (%copy-list-safe (ui-state-window-order state)))
         (widget-order (%copy-list-safe (ui-state-widget-order state)))
         (command-order (%copy-list-safe (ui-state-command-order state)))
         (tasks (%ordered-values task-order (ui-state-tasks state)))
         (windows (%ordered-values window-order (ui-state-windows state)))
         (widgets (%ordered-values widget-order (ui-state-widgets state)))
         (commands (and include-commands
                        (%ordered-values command-order (ui-state-commands state)))))
    (list :version *ui-snapshot-version*
          :tasks (mapcar #'%snapshot-task tasks)
          :task-order task-order
          :windows (mapcar #'%snapshot-window windows)
          :window-order window-order
          :widgets (mapcar #'%snapshot-widget widgets)
          :widget-order widget-order
          :commands (and include-commands (mapcar #'%snapshot-command commands))
          :command-order command-order
          :focus-widget-id (ui-state-focus-widget-id state)
          :next-task-id (ui-state-next-task-id state)
          :next-window-id (ui-state-next-window-id state)
          :next-widget-id (ui-state-next-widget-id state))))

(defun %restore-next-id (order)
  (let ((max-id 0))
    (dolist (id order)
      (when (and (stringp id) (> (length id) 0))
        (let ((pos (position #\- id :from-end t)))
          (when pos
            (let ((num (ignore-errors (parse-integer id :start (1+ pos) :junk-allowed t))))
              (when (and num (> num max-id))
                (setf max-id num)))))))
    (1+ max-id)))

(defun ui-state-from-snapshot (snapshot &key (command-init nil))
  (unless (and (listp snapshot) (getf snapshot :version))
    (error "Invalid UI snapshot"))
  (let ((state (make-ui-state)))
    (setf (ui-state-task-order state) (%copy-list-safe (getf snapshot :task-order)))
    (setf (ui-state-window-order state) (%copy-list-safe (getf snapshot :window-order)))
    (setf (ui-state-widget-order state) (%copy-list-safe (getf snapshot :widget-order)))
    (setf (ui-state-command-order state) (%copy-list-safe (getf snapshot :command-order)))
    (dolist (task (getf snapshot :tasks))
      (let ((id (getf task :id)))
        (when id
          (setf (gethash id (ui-state-tasks state))
                (make-ui-task :id id
                              :label (getf task :label)
                              :window-ids (%copy-list-safe (getf task :window-ids))
                              :active-window-id (getf task :active-window-id))))))
    (dolist (window (getf snapshot :windows))
      (let ((id (getf window :id)))
        (when id
          (setf (gethash id (ui-state-windows state))
                (make-ui-window :id id
                                :title (getf window :title)
                                :root-widget-id (getf window :root-widget-id)
                                :task-id (getf window :task-id))))))
    (dolist (widget (getf snapshot :widgets))
      (let ((id (getf widget :id)))
        (when id
          (setf (gethash id (ui-state-widgets state))
                (make-ui-widget :id id
                                :kind (getf widget :kind)
                                :props (%copy-list-safe (getf widget :props))
                                :children (%copy-list-safe (getf widget :children))
                                :command-id (getf widget :command-id)
                                :text (getf widget :text)
                                :state (getf widget :state))))))
    (dolist (command (getf snapshot :commands))
      (let ((id (getf command :id)))
        (when id
          (setf (gethash id (ui-state-commands state))
                (make-ui-command :id id :doc (getf command :doc) :enabled-p nil :handler nil)))))
    (setf (ui-state-focus-widget-id state) (getf snapshot :focus-widget-id))
    (setf (ui-state-next-task-id state)
          (or (getf snapshot :next-task-id)
              (%restore-next-id (ui-state-task-order state))))
    (setf (ui-state-next-window-id state)
          (or (getf snapshot :next-window-id)
              (%restore-next-id (ui-state-window-order state))))
    (setf (ui-state-next-widget-id state)
          (or (getf snapshot :next-widget-id)
              (%restore-next-id (ui-state-widget-order state))))
    (when (functionp command-init)
      (funcall command-init state))
    state))

(defun ui-save-snapshot (state &key (path *ui-persist-path*))
  (handler-case
      (let ((snapshot (ui-state->snapshot state)))
        (with-open-file (out path
                             :direction :output
                             :if-exists :supersede
                             :if-does-not-exist :create)
          (let ((*print-readably* t)
                (*print-circle* t)
                (*print-length* nil)
                (*print-level* nil))
            (prin1 snapshot out)))
        0)
    (error () -1)))

(defun ui-load-snapshot (&key (path *ui-persist-path*) (command-init nil))
  (handler-case
      (with-open-file (in path :direction :input)
        (let ((*read-eval* nil))
          (ui-state-from-snapshot (read in nil nil) :command-init command-init)))
    (error () nil)))

(defun %append-order (order id)
  (nconc order (list id)))

(defun %next-id (prefix counter)
  (format nil "~a-~d" prefix counter))

(defun %next-task-id (state)
  (let ((id (%next-id "task" (ui-state-next-task-id state))))
    (incf (ui-state-next-task-id state))
    id))

(defun %next-window-id (state)
  (let ((id (%next-id "window" (ui-state-next-window-id state))))
    (incf (ui-state-next-window-id state))
    id))

(defun %next-widget-id (state)
  (let ((id (%next-id "widget" (ui-state-next-widget-id state))))
    (incf (ui-state-next-widget-id state))
    id))

(defun ui-get-task (state task-id)
  (gethash task-id (ui-state-tasks state)))

(defun ui-get-window (state window-id)
  (gethash window-id (ui-state-windows state)))

(defun ui-get-widget (state widget-id)
  (gethash widget-id (ui-state-widgets state)))

(defun ui-get-command (state command-id)
  (gethash command-id (ui-state-commands state)))

(defun ui-add-task (state &key label id)
  (let* ((tid (or id (%next-task-id state)))
         (tasks (ui-state-tasks state)))
    (when (gethash tid tasks)
      (error "Task already exists: ~S" tid))
    (setf (gethash tid tasks)
          (make-ui-task :id tid :label label :window-ids nil :active-window-id nil))
    (setf (ui-state-task-order state)
          (%append-order (ui-state-task-order state) tid))
    (values state tid)))

(defun ui-add-window (state task-id &key title root-widget-id id)
  (let* ((task (ui-get-task state task-id)))
    (unless task
      (error "Unknown task: ~S" task-id))
    (let* ((wid (or id (%next-window-id state)))
           (windows (ui-state-windows state)))
      (when (gethash wid windows)
        (error "Window already exists: ~S" wid))
      (setf (gethash wid windows)
            (make-ui-window :id wid
                            :title title
                            :root-widget-id root-widget-id
                            :task-id task-id))
      (setf (ui-task-window-ids task)
            (%append-order (ui-task-window-ids task) wid))
      (when (null (ui-task-active-window-id task))
        (setf (ui-task-active-window-id task) wid))
      (setf (ui-state-window-order state)
            (%append-order (ui-state-window-order state) wid))
      (values state wid))))

(defun ui-add-widget (state kind &key props children command-id text id widget-state)
  (let* ((wid (or id (%next-widget-id state)))
         (widgets (ui-state-widgets state)))
    (when (gethash wid widgets)
      (error "Widget already exists: ~S" wid))
    (setf (gethash wid widgets)
          (make-ui-widget :id wid
                          :kind kind
                          :props props
                          :children children
                          :command-id command-id
                          :text text
                          :state widget-state))
    (setf (ui-state-widget-order state)
          (%append-order (ui-state-widget-order state) wid))
    (values state wid)))

(defun ui-register-command (state command-id handler &key doc enabled-p)
  (let ((commands (ui-state-commands state)))
    (setf (gethash command-id commands)
          (make-ui-command :id command-id
                           :doc doc
                           :enabled-p enabled-p
                           :handler handler))
    (unless (find command-id (ui-state-command-order state) :test #'equal)
      (setf (ui-state-command-order state)
            (%append-order (ui-state-command-order state) command-id)))
    state))

(defun ui-set-widget-text (state widget-id text)
  (let ((widget (ui-get-widget state widget-id)))
    (unless widget
      (error "Unknown widget: ~S" widget-id))
    (setf (ui-widget-text widget) text)
    state))

(defun ui-set-focus (state widget-id)
  (setf (ui-state-focus-widget-id state) widget-id)
  state)

(defun ui-enqueue-event (state event)
  (push event (ui-state-event-queue state))
  state)

(defun ui-enqueue-signal (state signal)
  (push signal (ui-state-signal-queue state))
  state)

(defmacro %drain-queue (place)
  `(let ((queue ,place))
     (setf ,place nil)
     (nreverse queue)))

(defun %event-type (event)
  (getf event :type))

(defun %event-flags (event)
  (getf event :flags 0))

(defun %event-target (event)
  (getf event :target-id))

(defun %base-target-id (target-id)
  (when (and target-id (stringp target-id))
    (let ((pos (position #\: target-id)))
      (when pos
        (subseq target-id 0 pos)))))

(defun %widget-prop (widget key)
  (when widget
    (cdr (assoc key (ui-widget-props widget) :test #'string=))))

(defun %resolve-command-id (state event)
  (let* ((target-id (%event-target event))
         (widget (and target-id (ui-get-widget state target-id))))
    (unless widget
      (let ((base (%base-target-id target-id)))
        (when base
          (setf widget (ui-get-widget state base)))))
    (or (and widget (ui-widget-command-id widget))
        (%widget-prop widget "data-command-id")
        nil)))

(defun %command-enabled (command state event)
  (let ((fn (ui-command-enabled-p command)))
    (if (functionp fn)
        (funcall fn state event)
        (values t nil))))

(defun %invoke-command (command state event)
  (let ((handler (ui-command-handler command)))
    (if (functionp handler)
        (funcall handler state event)
        state)))

(defun ui-handle-event (state event)
  (let* ((etype (%event-type event))
         (flags (%event-flags event))
         (target (%event-target event)))
    (cond
      ((eql etype :dispatch)
       (let* ((command-id (getf event :command-id))
              (command (and command-id (ui-get-command state command-id))))
         (if (null command)
             state
             (multiple-value-bind (ok reason) (%command-enabled command state (getf event :event))
               (declare (ignore reason))
               (if ok
                   (%invoke-command command state (getf event :event))
                   state)))))
      ((eql etype +ui-event-focus+)
       (ui-set-focus state target))
      ((eql etype +ui-event-blur+)
       (when (equal (ui-state-focus-widget-id state) target)
         (ui-set-focus state nil)))
      ((and (eql etype +ui-event-pointer+)
            (not (zerop (logand flags +ui-pointer-flag-down+))))
       (when target (ui-set-focus state target))
       (let ((command-id (%resolve-command-id state event)))
         (if command-id
             (ui-handle-event state (list :type :dispatch :command-id command-id :event event))
             state)))
      ((or (eql etype +ui-event-key+)
           (eql etype +ui-event-text+)
           (eql etype +ui-event-composition+)
           (eql etype +ui-event-wheel+))
       (let ((command-id (%resolve-command-id state event)))
         (if command-id
             (ui-handle-event state (list :type :dispatch :command-id command-id :event event))
             state)))
      (t state))))

(defun ui-handle-signal (state signal)
  (let ((stype (getf signal :type)))
    (cond
      ((and stype (string= stype "ui:interrupt"))
       (setf (ui-state-yield-reason state) "interrupt-pending")
       state)
      (t state))))

(defun ui-poll-and-enqueue (state &key (max-events 64) (max-bytes 65536) (allow-pending t))
  (multiple-value-bind (events result)
      (ui-poll-events :max-events max-events :max-bytes max-bytes :allow-pending allow-pending)
    (when events
      (dolist (event events)
        (ui-enqueue-event state event)))
    (%ui-maybe-yield-on-pending state result allow-pending)
    (values state result)))

(defun %inject-prop (props key value)
  (let ((existing (assoc key props :test #'string=)))
    (if existing
        (setf (cdr existing) value)
        (push (cons key value) props))
    props))

(defun %widget-props-with-ids (state widget)
  (let* ((props (copy-list (or (ui-widget-props widget) nil)))
         (wid (ui-widget-id widget)))
    (setf props (%inject-prop props "data-widget-id" wid))
    (when (ui-widget-command-id widget)
      (setf props (%inject-prop props "data-command-id" (ui-widget-command-id widget))))
    (when (and (ui-state-focus-widget-id state)
               (equal (ui-state-focus-widget-id state) wid))
      (setf props (%inject-prop props "data-focused" "true")))
    props))

(defun %widget->node (state widget)
  (let ((props (%widget-props-with-ids state widget)))
    (case (ui-widget-kind widget)
      (:label
       (ui-element "div" props (list (ui-text (or (ui-widget-text widget) "")))))
      (:button
       (let ((props2 (%inject-prop props "type" "button")))
         (ui-element "button" props2 (list (ui-text (or (ui-widget-text widget) ""))))))
      (:input
       (let ((props2 props))
         (when (ui-widget-text widget)
           (setf props2 (%inject-prop props2 "value" (ui-widget-text widget))))
         (ui-element "input" props2 nil)))
      (:container
       (let ((children (mapcar (lambda (child-id)
                                 (let ((child (ui-get-widget state child-id)))
                                   (when child
                                     (%widget->node state child))))
                               (or (ui-widget-children widget) nil))))
         (ui-element "div" props (remove nil children))))
      (:canvas
       (let ((props2 (if (assoc "data-canvas-scene" props :test #'string=)
                         props
                         (%inject-prop props "data-canvas-scene" "[]"))))
         (ui-element "canvas" props2 nil)))
      (:webgl
       (let ((props2 (if (assoc "data-webgl-scene" props :test #'string=)
                         props
                         (%inject-prop props "data-webgl-scene" "[]"))))
         (ui-element "canvas" props2 nil)))
      (t
       (ui-element "div" props (list (ui-text (or (ui-widget-text widget) ""))))))))

(defun %window->node (state window)
  (let* ((root-id (ui-window-root-widget-id window))
         (root (and root-id (ui-get-widget state root-id))))
    (ui-element "div"
                (list (cons "className" "ui-window")
                      (cons "data-window-id" (ui-window-id window)))
                (list
                 (ui-element "div"
                             '(("className" . "ui-window-title"))
                             (list (ui-text (or (ui-window-title window) ""))))
                 (ui-element "div"
                             '(("className" . "ui-window-body"))
                             (list (if root (%widget->node state root) (ui-text ""))))))))

(defun %task->node (state task)
  (let ((windows (mapcar (lambda (wid)
                           (let ((win (ui-get-window state wid)))
                             (when win (%window->node state win))))
                         (or (ui-task-window-ids task) nil))))
    (ui-element "div"
                (list (cons "className" "ui-task")
                      (cons "data-task-id" (ui-task-id task)))
                (remove nil windows))))

(defun ui-build-tree (state)
  (let ((tasks (mapcar (lambda (tid)
                         (let ((task (ui-get-task state tid)))
                           (when task (%task->node state task))))
                       (ui-state-task-order state))))
    (ui-element "div"
                '(("className" . "ui-root"))
                (remove nil tasks))))

(defun %drain-wasm-interrupt-signals (state)
  (let* ((sym (find-symbol "*WASM-UI-INTERRUPT-SIGNAL-QUEUE*" "CCL")))
    (when (and sym (boundp sym))
      (let ((queue (symbol-value sym)))
        (when queue
          (setf (symbol-value sym) nil)
          (dolist (signal (nreverse queue))
            (ui-enqueue-signal state signal))))))
  state)

(defun ui-run-turn (state &key (render t))
  (setf (ui-state-turn-phase state) :signals)
  (%drain-wasm-interrupt-signals state)
  (dolist (signal (%drain-queue (ui-state-signal-queue state)))
    (setf state (ui-handle-signal state signal)))
  (setf (ui-state-turn-phase state) :events)
  (dolist (event (%drain-queue (ui-state-event-queue state)))
    (setf state (ui-handle-event state event)))
  (setf (ui-state-turn-phase state) :render)
  (let ((tree (ui-build-tree state)))
    (when render
      (ui-render-tree tree))
    (setf (ui-state-turn-phase state) :idle)
    (values state tree)))

(defun ui-demo-state ()
  (let* ((canvas-scene
           (concatenate
            'string
            "[{\"id\":\"bottom\",\"kind\":\"rect\",\"bounds\":{\"x\":0,\"y\":0,\"width\":50,\"height\":50},\"props\":{\"fill\":\"#000\"}},"
            "{\"id\":\"top\",\"kind\":\"rect\",\"bounds\":{\"x\":5,\"y\":5,\"width\":20,\"height\":20},\"props\":{\"fill\":\"#f00\"}}]"))
         (webgl-scene
           (concatenate
            'string
            "[{\"id\":\"bottom\",\"kind\":\"rect\",\"bounds\":{\"x\":0,\"y\":0,\"width\":40,\"height\":40},\"props\":{\"fill\":\"#000\"}},"
            "{\"id\":\"top\",\"kind\":\"rect\",\"bounds\":{\"x\":8,\"y\":8,\"width\":16,\"height\":16},\"props\":{\"fill\":\"#0f0\"}}]"))
         (state (make-ui-state)))
    (multiple-value-bind (_state task-id)
        (ui-add-task state :label "Demo" :id "demo-task")
      (declare (ignore _state))
      (multiple-value-bind (_state button-id)
          (ui-add-widget state :button
                         :id "demo-button"
                         :text "Click"
                         :command-id "demo.click")
        (declare (ignore _state))
        (multiple-value-bind (_state label-id)
            (ui-add-widget state :label
                           :id "demo-label"
                           :text "Ready")
          (declare (ignore _state))
          (multiple-value-bind (_state canvas-id)
              (ui-add-widget state :canvas
                             :id "demo-canvas"
                             :command-id "demo.canvas"
                             :props `(("data-canvas-scene" . ,canvas-scene)))
            (declare (ignore _state))
            (multiple-value-bind (_state webgl-id)
                (ui-add-widget state :webgl
                               :id "demo-webgl"
                               :command-id "demo.webgl"
                               :props `(("data-webgl-scene" . ,webgl-scene)))
              (declare (ignore _state))
              (multiple-value-bind (_state root-id)
                  (ui-add-widget state :container
                                 :id "demo-root"
                                 :children (list button-id label-id canvas-id webgl-id))
                (declare (ignore _state))
                (ui-add-window state task-id
                               :id "demo-window"
                               :title "Demo"
                               :root-widget-id root-id)
                (ui-register-command
                 state
                 "demo.click"
                 (lambda (st event)
                   (declare (ignore event))
                   (ui-set-widget-text st label-id "Clicked"))
                 :doc "Demo click handler")
                (ui-register-command
                 state
                 "demo.canvas"
                 (lambda (st event)
                   (let ((target (or (getf event :target-id) "")))
                     (ui-set-widget-text st label-id (format nil "Canvas ~a" target))))
                 :doc "Demo canvas handler")
                (ui-register-command
                 state
                 "demo.webgl"
                 (lambda (st event)
                   (let ((target (or (getf event :target-id) "")))
                     (ui-set-widget-text st label-id (format nil "WebGL ~a" target))))
                 :doc "Demo webgl handler")
                state))))))))

(defun ui-demo-turn (&optional (state (ui-demo-state)))
  (ui-run-turn state :render t))

(defun ui-demo-label-text (state)
  (let ((label (ui-get-widget state "demo-label")))
    (when label
      (or (ui-widget-text label) ""))))

(defun ui-demo-set-label (state value)
  (if (ui-get-widget state "demo-label")
      (ui-set-widget-text state "demo-label" value)
      state))

(defun ui-demo-label-state (state)
  (let ((text (ui-demo-label-text state)))
    (cond
      ((string= text "Ready") 1)
      ((string= text "Persisted") 2)
      ((string= text "Dirty") 3)
      ((string= text "Clicked") 4)
      (t 0))))

(defun ui-open-inspector (state &key task-id)
  (let* ((tid (or task-id (car (ui-state-task-order state))))
         (state (if tid state (progn (multiple-value-bind (st new-id)
                                        (ui-add-task state :label "System" :id "system-task")
                                      (declare (ignore new-id))
                                      st))))
         (tid (or tid "system-task")))
    (multiple-value-bind (state title-id)
        (ui-add-widget state :label :id "inspector-title" :text "Inspector")
      (multiple-value-bind (state root-id)
          (ui-add-widget state :container :id "inspector-root" :children (list title-id))
        (ui-add-window state tid
                       :id "inspector-window"
                       :title "Inspector"
                       :root-widget-id root-id)))))

(defun ui-open-debugger (state &key task-id (message "Debugger"))
  (let* ((tid (or task-id (car (ui-state-task-order state))))
         (state (if tid state (progn (multiple-value-bind (st new-id)
                                        (ui-add-task state :label "System" :id "system-task")
                                      (declare (ignore new-id))
                                      st))))
         (tid (or tid "system-task")))
    (multiple-value-bind (state title-id)
        (ui-add-widget state :label :id "debugger-title" :text message)
      (multiple-value-bind (state root-id)
          (ui-add-widget state :container :id "debugger-root" :children (list title-id))
        (ui-add-window state tid
                       :id "debugger-window"
                       :title "Debugger"
                       :root-widget-id root-id)))))

;;;; ------------------------------------------------------------
;;;; Smoke entrypoint (Phase 5 bring-up)
;;;; ------------------------------------------------------------

(defvar *wasm-ui-demo-state* nil)

(defun %ensure-wasm-ui-demo-state ()
  (or *wasm-ui-demo-state*
      (setf *wasm-ui-demo-state* (ui-demo-state))))

(defun ccl::wasm-ui-turn ()
  "Run one UI turn: poll events (non-blocking), then render."
  (let ((state (%ensure-wasm-ui-demo-state)))
    (multiple-value-bind (st poll-result)
        (ui-poll-and-enqueue state :allow-pending nil)
      (setf state st)
      (multiple-value-bind (next-state _tree)
          (ui-run-turn state :render t)
        (declare (ignore _tree))
        (setf *wasm-ui-demo-state* next-state)
        (if (and poll-result (numberp poll-result))
            poll-result
            0)))))

(defun ccl::wasm-ui-mark-persisted ()
  (let ((state (%ensure-wasm-ui-demo-state)))
    (setf *wasm-ui-demo-state* (ui-demo-set-label state "Persisted"))
    0))

(defun ccl::wasm-ui-mark-dirty ()
  (let ((state (%ensure-wasm-ui-demo-state)))
    (setf *wasm-ui-demo-state* (ui-demo-set-label state "Dirty"))
    0))

(defun ccl::wasm-ui-label-state ()
  (let ((state (%ensure-wasm-ui-demo-state)))
    (ui-demo-label-state state)))

(defun ccl::wasm-ui-save ()
  (let ((state (%ensure-wasm-ui-demo-state)))
    (ui-save-snapshot state)))

(defun ccl::wasm-ui-restore ()
  (let ((state (ui-load-snapshot)))
    (when state
      (setf *wasm-ui-demo-state* state)
      (values))
    (if state 0 -1)))
