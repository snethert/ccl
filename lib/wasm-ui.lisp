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

(defun %widget-prop (widget key)
  (when widget
    (cdr (assoc key (ui-widget-props widget) :test #'string=))))

(defun %resolve-command-id (state event)
  (let* ((target-id (%event-target event))
         (widget (and target-id (ui-get-widget state target-id))))
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
  (let ((state (make-ui-state)))
    (multiple-value-bind (_state task-id)
        (ui-add-task state :label "Demo")
      (declare (ignore _state))
      (multiple-value-bind (_state button-id)
          (ui-add-widget state :button
                         :text "Click"
                         :command-id "demo.click")
        (declare (ignore _state))
        (multiple-value-bind (_state label-id)
            (ui-add-widget state :label
                           :text "Ready")
          (declare (ignore _state))
          (multiple-value-bind (_state root-id)
              (ui-add-widget state :container
                             :children (list button-id label-id))
            (declare (ignore _state))
            (ui-add-window state task-id
                           :title "Demo"
                           :root-widget-id root-id)
            (ui-register-command
             state
             "demo.click"
             (lambda (st event)
               (declare (ignore event))
               (ui-set-widget-text st label-id "Clicked"))
             :doc "Demo click handler")
            state))))))

(defun ui-demo-turn (&optional (state (ui-demo-state)))
  (ui-run-turn state :render t))

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
