;;;-*-Mode: LISP; Package: CCL -*-
;;;
;;; Copyright 1994-2009 Clozure Associates
;;;
;;; Licensed under the Apache License, Version 2.0 (the "License");
;;; you may not use this file except in compliance with the License.
;;; You may obtain a copy of the License at
;;;
;;;     http://www.apache.org/licenses/LICENSE-2.0
;;;
;;; Unless required by applicable law or agreed to in writing, software
;;; distributed under the License is distributed on an "AS IS" BASIS,
;;; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
;;; See the License for the specific language governing permissions and
;;; limitations under the License.

; l1-readloop-lds.lisp

(in-package "CCL")


(defvar *read-loop-function* 'read-loop)

(defun run-read-loop (&rest args)
  (declare (dynamic-extent args))
  (apply *read-loop-function* args))

#+wasm32-target
(defun toplevel-loop ()
  (loop
    (runtime-bridge-pump-commands)
    (let ((yielded
           (if *wasm-yield-on-eagain*
             (catch :wasm-yield
               (progn
                 (if (eq (catch :toplevel
                           (run-read-loop :break-level 0)) $xstkover)
                   (format t "~&;[Stacks reset due to overflow.]")
                   (when (eq *current-process* *initial-process*)
                     (toplevel)))
                 nil))
             (progn
               (if (eq (catch :toplevel
                         (run-read-loop :break-level 0)) $xstkover)
                 (format t "~&;[Stacks reset due to overflow.]")
                 (when (eq *current-process* *initial-process*)
                   (toplevel)))
               nil))))
      (when yielded
        (return yielded)))))

#-wasm32-target
(defun toplevel-loop ()
  (loop
    (if (eq (catch :toplevel 
              (run-read-loop :break-level 0 )) $xstkover)
      (format t "~&;[Stacks reset due to overflow.]")
      (when (eq *current-process* *initial-process*)
        (toplevel)))))


(defvar *defined-toplevel-commands* ())
(defvar *active-toplevel-commands* ())

(defun %define-toplevel-command (group-name key name fn doc args)
  (let* ((group (or (assoc group-name *defined-toplevel-commands*)
		    (car (push (list group-name)
			       *defined-toplevel-commands*))))
	 (pair (assoc key (cdr group) :test #'eq)))
    (if pair
      (rplacd pair (list* fn doc args))
      (push (cons key (list* fn doc args)) (cdr group))))
  name)

(define-toplevel-command 
    :global y (&optional p) "Yield control of terminal-input to process
whose name or ID matches <p>, or to any process if <p> is null"
    (%%yield-terminal-to (if p (find-process p))))	;may be nil


(define-toplevel-command
    :global kill (p) "Kill process whose name or ID matches <p>"
    (let* ((proc (find-process p)))
      (if proc
	(process-kill proc))))

(define-toplevel-command 
    :global proc (&optional p) "Show information about specified process <p>/all processes"
    (flet ((show-process-info (proc)
	     (format t "~&~d : ~a ~a ~25t[~a] "
		     (process-serial-number proc)
		     (if (eq proc *current-process*)
		       "->"
		       "  ")
		     (process-name proc)
		     (process-whostate proc))
	     (let* ((suspend-count (process-suspend-count proc)))
	       (if (and suspend-count (not (eql 0 suspend-count)))
		 (format t " (Suspended)")))
	     (let* ((terminal-input-shared-resource
		     (if (typep *terminal-io* 'two-way-stream)
		       (input-stream-shared-resource
			(two-way-stream-input-stream *terminal-io*)))))
	       (if (and terminal-input-shared-resource
			(%shared-resource-requestor-p
			 terminal-input-shared-resource proc))
		 (format t " (Requesting terminal input)")))
	     (fresh-line)))
      (if p
	(let* ((proc (find-process p)))
	  (if (null proc)
	    (format t "~&;; not found - ~s" p)
	    (show-process-info proc)))
	(dolist (proc (all-processes) (values))
	  (show-process-info proc)))))

(define-toplevel-command :global cd (dir) "Change to directory DIR (e.g., #p\"ccl:\" or \"/some/dir\")" (setf (current-directory) dir) (toplevel-print (list (current-directory))))

(define-toplevel-command :global pwd () "Print the pathame of the current directory" (toplevel-print (list (current-directory))))



(defun list-restarts ()
  (let ((prefix (format nil (format nil "~@[~D ~]>" (and (plusp *break-level*) *break-level*)))))
    (when *break-condition*
      (let ((*error-output* *debug-io*))
        (%break-message nil *break-condition* *top-error-frame* prefix)))
    (format *debug-io* "~&~A Type (:C <n>) to invoke one of the following restarts:" prefix))
  (display-restarts))

(define-toplevel-command :break pop () "exit current break loop" (abort-break))
(define-toplevel-command :break a () "exit current break loop" (abort-break))
(define-toplevel-command :break go () "continue" (continue))
(define-toplevel-command :break q () "return to toplevel" (toplevel))
(define-toplevel-command :break r () "show error and list restarts" (list-restarts))


(define-toplevel-command :break nframes ()
  "print the number of stack frames accessible from this break loop"
  (do* ((p *break-frame* (parent-frame p nil))
        (i 0 )
        (last (last-frame-ptr)))
      ((eql p last) (toplevel-print (list i)))
    (declare (fixnum i))
    (when (function-frame-p p nil)
      (incf i))))

(define-toplevel-command :global ? () "help"
  (format t "~&The following toplevel commands are available:")
  (when *default-integer-command*
    (format t "~& <n>  ~8Tthe same as (~s <n>)" (car *default-integer-command*)))
  (dolist (g *active-toplevel-commands*)
    (dolist (c (cdr g))
      (let* ((command (car c))
	     (doc (caddr c))
	     (args (cdddr c)))
	(if args
	  (format t "~& (~S~{ ~A~}) ~8T~A" command args doc)
	  (format t "~& ~S  ~8T~A" command doc)))))
  (format t "~&Any other form is evaluated and its results are printed out."))


(define-toplevel-command :break b (&key start count show-frame-contents) "backtrace"
  (when *break-frame*
      (print-call-history :detailed-p show-frame-contents
                          :origin *break-frame*
                          :count count
                          :start-frame-number (or start 0))))

(define-toplevel-command :break c (&optional n) "Choose restart <n>. If no <n>, continue"
  (if n
   (select-restart n)
   (continue)))

(define-toplevel-command :break f (n) "Show backtrace frame <n>"
   (print-call-history :origin *break-frame*
                       :start-frame-number n
                       :count 1
                       :detailed-p t))

(define-toplevel-command :break return-from-frame (i &rest values) "Return VALUES from the I'th stack frame"
  (let* ((frame-sp (nth-function-frame  i *break-frame* nil)))
    (if frame-sp
      (apply #'return-from-frame frame-sp values))))

(define-toplevel-command :break apply-in-frame (i function &rest args) "Applies FUNCTION to ARGS in the execution context of the Ith stack frame"
  (let* ((frame-sp (nth-function-frame  i *break-frame* nil)))
    (if frame-sp
      (apply-in-frame frame-sp function args))))
                         
                         

(define-toplevel-command :break raw (n) "Show raw contents of backtrace frame <n>"
   (print-call-history :origin *break-frame*
                       :start-frame-number n
                       :count 1
                       :detailed-p :raw))

(define-toplevel-command :break v (n frame-number) "Return value <n> in frame <frame-number>"
  (let* ((frame-sp (nth-function-frame frame-number *break-frame* nil)))
    (if frame-sp
      (toplevel-print (list (nth-value-in-frame frame-sp n nil))))))

(define-toplevel-command :break arg (name frame-number) "Return value of argument named <name> in frame <frame-number>"
  (let* ((frame-sp (nth-function-frame frame-number *break-frame* nil)))
    (when frame-sp
      (multiple-value-bind (lfun pc) (cfp-lfun frame-sp)
        (when (and lfun pc)
          (let* ((unavailable (cons nil nil)))
            (declare (dynamic-extent unavailable))
            (let* ((value (arg-value nil frame-sp lfun pc unavailable name)))
              (if (eq value unavailable)
                (format *debug-io* "~&;; Can't determine value of ~s in frame ~s." name frame-number)
                (toplevel-print (list value))))))))))

(define-toplevel-command :break set-arg (name frame-number new) "Set value of argument named <name> in frame <frame-number> to value <new>."
  (let* ((frame-sp (nth-function-frame frame-number *break-frame* nil)))
    (when frame-sp
      (multiple-value-bind (lfun pc) (cfp-lfun frame-sp)
        (when (and lfun pc)
          (or (set-arg-value nil frame-sp lfun pc name new)
              (format *debug-io* "~&;; Can't change value of ~s in frame ~s." name frame-number)))))))
   

(define-toplevel-command :break local (name frame-number) "Return value of local denoted by <name> in frame <frame-number> <name> can either be a symbol - in which case the most recent
binding of that symbol is used - or an integer index into the frame's set of local bindings."
  (let* ((frame-sp (nth-function-frame frame-number *break-frame* nil)))
    (when frame-sp
      (multiple-value-bind (lfun pc) (cfp-lfun frame-sp)
        (when (and lfun pc)
          (let* ((unavailable (cons nil nil)))
            (declare (dynamic-extent unavailable))
            (let* ((value (local-value nil frame-sp lfun pc unavailable name)))
              (if (eq value unavailable)
                (format *debug-io* "~&;; Can't determine value of ~s in frame ~s." name frame-number)
                (toplevel-print (list value))))))))))

(define-toplevel-command :break set-local (name frame-number new) "Set value of argument denoted <name> (see :LOCAL) in frame <frame-number> to value <new>."
  (let* ((frame-sp (nth-function-frame frame-number *break-frame* nil)))
    (when frame-sp
      (multiple-value-bind (lfun pc) (cfp-lfun frame-sp)
        (when (and lfun pc)
          (or (set-local-value nil frame-sp lfun pc name new)
              (format *debug-io* "~&;; Can't change value of ~s in frame ~s." name frame-number)))))))


(define-toplevel-command :break form (frame-number)
   "Return a form which looks like the call which established the stack frame identified by <frame-number>.  This is only well-defined in certain cases: when the function is globally named and not a lexical closure and when it was compiled with *SAVE-LOCAL-SYMBOLS* in effect."
   (let* ((form (dbg-form frame-number)))
     (when form
       (let* ((*print-level* (default-print-level *backtrace-print-level*))
              (*print-length* (default-print-length *backtrace-print-length*)))
         (toplevel-print (list form))))))

;;; Ordinarily, form follows function.
(define-toplevel-command :break function (frame-number)
  "Returns the function invoked in backtrace frame <frame-number>.  This may be useful for, e.g., disassembly"
  (let* ((cfp (nth-function-frame frame-number *break-frame* nil)))
    (when (and cfp (not (catch-csp-p cfp nil)))
      (let* ((function (cfp-lfun cfp)))
        (when function
          (toplevel-print (list function)))))))
  


          

  

(defun %use-toplevel-commands (group-name)
  ;; Push the whole group
  (pushnew (assoc group-name *defined-toplevel-commands*)
	   *active-toplevel-commands*
	   :key #'(lambda (x) (car x))))  ; #'car not defined yet ...

(%use-toplevel-commands :global)

(defparameter *toplevel-commands-dwim* t
 "If true, tries to interpret otherwise-erroneous toplevel expressions as commands.
In addition, will suppress standard error handling for expressions that look like
commands but aren't")

(defvar *default-integer-command* nil
  "If non-nil, should be (keyword  min max)), causing integers between min and max to be
  interpreted as (keyword integer)")

(defun check-toplevel-command (form)
  (when (and *default-integer-command*
             (integerp form)
             (<= (cadr *default-integer-command*) form (caddr *default-integer-command*)))
    (setq form `(,(car *default-integer-command*) ,form)))
  (let* ((cmd (if (consp form) (car form) form))
         (args (if (consp form) (cdr form))))
    (when (or (keywordp cmd)
              (and *toplevel-commands-dwim*
                   (non-nil-symbol-p cmd)
                   (not (if (consp form)
                          (fboundp cmd)
                          (or (boundp cmd)
                              (nth-value 1 (gethash cmd *symbol-macros*)))))
                   ;; Use find-symbol so don't make unneeded keywords.
                   (setq cmd (find-symbol (symbol-name cmd) :keyword))))
      (when (eq cmd :help) (setq cmd :?))
      (flet ((run (cmd form)
               (or (dolist (g *active-toplevel-commands*)
                     (let* ((pair (assoc cmd (cdr g))))
                       (when pair 
                         (apply (cadr pair) args)
                         (return t))))
                   ;; Try to detect user mistyping a command
                   (when (and *toplevel-commands-dwim*
                              (if (consp form)
                                (and (keywordp (%car form)) (not (fboundp (%car form))))
                                (keywordp form)))
                     (error "Unknown command ~s" cmd)))))
        (declare (dynamic-extent #'run))
        (if *toplevel-commands-dwim*
          (block nil
            (handler-bind ((error (lambda (c)
                                    (format t "~&~a" c)
                                    (return t))))
              (run cmd form)))
          (run cmd form))))))

(defparameter *quit-on-eof* nil)

(defparameter *consecutive-eof-limit* 2 "max number of consecutive EOFs at a given break level, before we give up and abruptly exit.")

(defmethod stream-eof-transient-p (stream)
  (let ((fd (stream-device stream :input)))
    (and fd (eof-transient-p fd))))

(defvar *save-interactive-source-locations* t)

;;; This is the part common to toplevel loop and inner break loops.
(defun read-loop (&key (input-stream *standard-input*)
                       (output-stream *standard-output*)
                       (break-level *break-level*)
		       (prompt-function #'(lambda (stream)
                                            (when (and *show-available-restarts* *break-condition*)
                                              (list-restarts)
                                              (setf *show-available-restarts* nil))
                                            (print-listener-prompt stream t))))
  (let* ((*break-level* break-level)
         (*last-break-level* break-level)
         (*loading-file-source-file* nil)
         (*loading-toplevel-location* nil)
         *in-read-loop*
         *** ** * +++ ++ + /// // / -
         (eof-value (cons nil nil))
         (eof-count 0)
         (*show-available-restarts* (and *show-restarts-on-break* *break-condition*))
         (map (make-hash-table :test #'eq :shared nil)))
    (declare (dynamic-extent eof-value))
    (loop
      (restart-case
       (catch :abort                    ;last resort...
         (loop
           (catch-cancel
            (loop                
              (setq *in-read-loop* nil
                    *break-level* break-level)
              (multiple-value-bind (form env print-result)
                  (toplevel-read :input-stream input-stream
                                 :output-stream output-stream
                                 :prompt-function prompt-function
                                 :eof-value eof-value
				 :map (when *save-interactive-source-locations*
                                        (clrhash map)
                                        map))
                (if (eq form eof-value)
                  (progn
                    (when (> (incf eof-count) *consecutive-eof-limit*)
                      #+wasm32-target
                      (error "readloop-lds exit is not supported on wasm")
                      #-wasm32-target
                      (#_ _exit 0))
                    (if (and (not *batch-flag*)
                             (not *quit-on-eof*)
                             (stream-eof-transient-p input-stream))
                      (progn
                        (stream-clear-input input-stream)
                        (abort-break))
                      (exit-interactive-process *current-process*)))
                  (let ((*nx-source-note-map* (and *save-interactive-source-locations* map)))
                    (setq eof-count 0)
                    (or (check-toplevel-command form)
                        (let* ((values (toplevel-eval form env)))
                          (if print-result (toplevel-print values)))))))))
           (format *terminal-io* "~&Cancelled")))
       (abort () :report (lambda (stream)
                           (if (eq break-level 0)
                             (format stream "Return to toplevel.")
                             (format stream "Return to break level ~D." break-level)))
              #|                        ; Handled by interactive-abort
                                        ; go up one more if abort occurred while awaiting/reading input               
              (when (and *in-read-loop* (neq break-level 0))
              (abort))
              |#
               )
       (abort-break () :report (lambda (stream)
                                 (if (eq break-level 0)
                                     (format stream "Exit toplevel.")
                                     (format stream "Exit break level ~D." break-level)))
                    (unless (eq break-level 0)
                      (abort))))
       (clear-input input-stream)
      (format output-stream "~%"))))

;;; The first non-whitespace character available on INPUT-STREAM is a colon.
;;; Try to interpret the line as a colon command (or possibly just a keyword.)
(defun read-command-or-keyword (input-stream eof-value)
  (let* ((line (read-line input-stream nil eof-value)))
    (if (eq line eof-value)
      eof-value
      (let* ((in (make-string-input-stream line))
             (keyword (read in nil eof-value)))
        (if (eq keyword eof-value)
          eof-value
          (if (not (keywordp keyword))
            keyword
            (collect ((params))
              (loop
                (let* ((param (read in nil eof-value)))
                  (if (eq param eof-value)
                    (return
                      (let* ((params (params)))
                        (if params
                          (cons keyword params)
                          keyword)))
                    (params (eval param))))))))))))

;;; Read a form from the specified stream.
(defun toplevel-read (&key (input-stream *standard-input*)
                           (output-stream *standard-output*)
                           (prompt-function #'print-listener-prompt)
                           (eof-value *eof-value*)
		           (map nil))
  (force-output output-stream)
  (funcall prompt-function output-stream)
  (read-toplevel-form input-stream :eof-value eof-value :map map))

(defvar *always-eval-user-defvars* nil)

(defun process-single-selection (form)
  (if (and *always-eval-user-defvars*
           (listp form) (eq (car form) 'defvar) (cddr form))
    `(defparameter ,@(cdr form))
    form))

(defun toplevel-eval (form &optional env)
  (destructuring-bind (vars . vals) (or env '(nil . nil))
    (progv vars vals
      (setq +++ ++ ++ + + - - form)
      (unwind-protect
           (let* ((package *package*)
                  (values (multiple-value-list (cheap-eval-in-environment form nil))))
             (unless (eq package *package*)
               ;; If changing a local value (e.g. buffer-local), not useful to notify app
               ;; without more info.  Perhaps should have a *source-context* that can send along?
               (unless (member '*package* vars)
                 (application-ui-operation *application* :note-current-package *package*)))
             values)
        (loop for var in vars as pval on vals
              do (setf (car pval) (symbol-value var)))))))

#-wasm32-target
(defun runtime-bridge-emit-output (&rest _args)
  (declare (ignore _args))
  nil)

#-wasm32-target
(defun runtime-bridge-pump-commands (&rest _args)
  (declare (ignore _args))
  nil)

#-wasm32-target
(defun runtime-bridge-emit-debugger-snapshot (&rest _args)
  (declare (ignore _args))
  nil)

#+wasm32-target
(progn
  (defconstant +kernel-op-runtime-event+ #x23)
  (defconstant +kernel-op-runtime-command-poll+ #x24)
  (defconstant +kernel-status-pending+ 0)
  (defconstant +kernel-status-done+ 1)
  (defconstant +kernel-status-error+ 2)
  (defconstant +runtime-command-frame-version+ 1)
  (defconstant +runtime-command-max-bytes+ 65536)

  (defvar *runtime-bridge-enabled* t)
  (defvar *runtime-bridge-job-id* nil)
  (defvar *runtime-bridge-stream-id* "repl")
  (defvar *runtime-command-enabled* t)
  (defvar *runtime-command-stream-id* "commands")
  (defvar *runtime-bridge-seq* 0)
  (defvar *runtime-bridge-recording-counter* 0)
  (defvar *runtime-debugger-error-counter* 0)
  (defvar *runtime-debugger-current-error-id* nil)
  (defvar *runtime-debugger-current-condition* nil)

  (defun runtime-bridge--now-ms ()
    (let ((seconds (- (get-universal-time) unix-to-universal-time)))
      (* seconds 1000)))

  (defun runtime-bridge--json-escape (string)
    (with-output-to-string (out)
      (loop for ch across string do
        (case ch
          (#\" (write-string "\\\"" out))
          (#\\ (write-string "\\\\" out))
          (#\Backspace (write-string "\\b" out))
          (#\Page (write-string "\\f" out))
          (#\Newline (write-string "\\n" out))
          (#\Return (write-string "\\r" out))
          (#\Tab (write-string "\\t" out))
          (t
           (let ((code (char-code ch)))
             (if (< code 32)
               (format out "\\u~4,'0x" code)
               (write-char ch out))))))))

  (defun runtime-bridge--json-object-p (value)
    (and (listp value)
         (every #'consp value)
         (every (lambda (pair)
                  (or (stringp (car pair)) (symbolp (car pair))))
                value)))

  (defun runtime-bridge--json-write (value stream)
    (cond
      ((null value) (write-string "null" stream))
      ((eq value t) (write-string "true" stream))
      ((stringp value)
       (write-char #\" stream)
       (write-string (runtime-bridge--json-escape value) stream)
       (write-char #\" stream))
      ((integerp value) (princ value stream))
      ((floatp value) (princ value stream))
      ((vectorp value)
       (write-char #\[ stream)
       (loop for i from 0 below (length value) do
         (when (> i 0) (write-string "," stream))
         (runtime-bridge--json-write (aref value i) stream))
       (write-char #\] stream))
      ((runtime-bridge--json-object-p value)
       (write-char #\{ stream)
       (loop for (key . val) in value
             for idx from 0 do
               (when (> idx 0) (write-string "," stream))
               (runtime-bridge--json-write (string key) stream)
               (write-char #\: stream)
               (runtime-bridge--json-write val stream))
       (write-char #\} stream))
      ((listp value)
       (let ((vec (coerce value 'vector)))
         (runtime-bridge--json-write vec stream)))
      (t
       (runtime-bridge--json-write (format nil "~s" value) stream))))

  (defun runtime-bridge--json-string (value)
    (with-output-to-string (out)
      (runtime-bridge--json-write value out)))

  (defun runtime-bridge--encode-output (values)
    (let* ((recording-id (format nil "rec-~d" (incf *runtime-bridge-recording-counter*)))
           (job-id *runtime-bridge-job-id*)
           (stream-id *runtime-bridge-stream-id*)
           (ts (runtime-bridge--now-ms))
           (entries nil)
           (anchors nil)
           (last-seq nil))
      (dolist (val values)
        (let* ((text (with-output-to-string (s) (write val :stream s)))
               (seq (incf *runtime-bridge-seq*))
               (entry-id (format nil "ent-~d" seq))
               (anchor-id (format nil "anc-~d" seq))
               (entry (list (cons "id" entry-id)
                            (cons "recordingId" recording-id)
                            (cons "kind" "text")
                            (cons "streamId" stream-id)
                            (cons "seq" seq)
                            (cons "ts" ts)
                            (cons "text" text)
                            (cons "anchorId" anchor-id)))
               (anchor (list (cons "id" anchor-id)
                             (cons "entryId" entry-id)
                             (cons "range" (list (cons "start" 0)
                                                 (cons "end" (length text))))
                             (cons "path" #()))))
          (push entry entries)
          (push anchor anchors)
          (setf last-seq seq)))
      (let* ((recording (list (cons "id" recording-id)
                              (cons "jobId" job-id)
                              (cons "status" "ok")
                              (cons "streamId" stream-id)))
             (payload (list (cons "recording" recording)
                            (cons "entries" (coerce (nreverse entries) 'vector))
                            (cons "anchors" (coerce (nreverse anchors) 'vector))))
             (envelope (list (cons "version" 1)
                             (cons "kind" "runtime.output")
                             (cons "jobId" job-id)
                             (cons "streamId" stream-id)
                             (cons "requestId" nil)
                             (cons "seq" last-seq)
                             (cons "ts" ts)
                             (cons "payload" payload)
                             (cons "error" nil))))
        (runtime-bridge--json-string envelope))))

  (defun runtime-bridge--emit-json (json)
    (let* ((bytes (encode-string-to-octets json :external-format :utf-8))
           (len (length bytes)))
      (ccl:with-pointer-to-ivector (ptr bytes)
        (let ((request-id (ccl:external-call "kernel_request"
                                             :unsigned-long +kernel-op-runtime-event+
                                             :address ptr
                                             :unsigned-long len
                                             :unsigned-long)))
          (unwind-protect
               (let ((status (ccl:external-call "kernel_poll"
                                                :unsigned-long request-id
                                                :unsigned-long)))
                 (when (= status +kernel-status-pending+)
                   (setf status (ccl:external-call "kernel_poll"
                                                   :unsigned-long request-id
                                                   :unsigned-long)))
                 (when (or (= status +kernel-status-done+) (= status +kernel-status-error+))
                   (ignore-errors
                     (ccl:external-call "kernel_result"
                                        :unsigned-long request-id
                                        :signed-long))))
            (ccl:external-call "kernel_drop_request"
                               :unsigned-long request-id
                               :void))))))

  (defun runtime-bridge--emit-message (kind payload &key request-id stream-id error)
    (let* ((ts (runtime-bridge--now-ms))
           (seq (incf *runtime-bridge-seq*))
           (envelope (list (cons "version" 1)
                           (cons "kind" kind)
                           (cons "jobId" *runtime-bridge-job-id*)
                           (cons "streamId" (or stream-id *runtime-command-stream-id*))
                           (cons "requestId" request-id)
                           (cons "seq" seq)
                           (cons "ts" ts)
                           (cons "payload" payload)
                           (cons "error" error))))
      (runtime-bridge--emit-json (runtime-bridge--json-string envelope))))

  (defun runtime-command--u32 (bytes offset)
    (logior (aref bytes offset)
            (ash (aref bytes (+ offset 1)) 8)
            (ash (aref bytes (+ offset 2)) 16)
            (ash (aref bytes (+ offset 3)) 24)))

  (defun runtime-command--decode-string (bytes start len)
    (decode-string-from-octets bytes
                               :start start
                               :end (+ start len)
                               :external-format :utf-8))

  (defun runtime-command--decode-frame (bytes)
    (let* ((n (length bytes)))
      (when (< n 24)
        (return-from runtime-command--decode-frame nil))
      (let* ((version (runtime-command--u32 bytes 0))
             (invocation-len (runtime-command--u32 bytes 4))
             (command-len (runtime-command--u32 bytes 8))
             (args-len (runtime-command--u32 bytes 12))
             (context-len (runtime-command--u32 bytes 16))
             (total (+ 24 invocation-len command-len args-len context-len)))
        (when (or (/= version +runtime-command-frame-version+)
                  (/= total n))
          (return-from runtime-command--decode-frame nil))
        (let* ((offset 24)
               (invocation-id (runtime-command--decode-string bytes offset invocation-len)))
          (incf offset invocation-len)
          (let* ((command-id (runtime-command--decode-string bytes offset command-len)))
            (incf offset command-len)
            (let* ((args-form-string (runtime-command--decode-string bytes offset args-len)))
              (incf offset args-len)
              (let* ((context-form-string (runtime-command--decode-string bytes offset context-len)))
                (list :invocation-id invocation-id
                      :command-id command-id
                      :args-form-string args-form-string
                      :context-form-string context-form-string))))))))

  (defun runtime-command--safe-read-form (string)
    (let ((eof (list :runtime-command-invalid)))
      (handler-case
          (multiple-value-bind (value pos) (read-from-string string nil eof)
            (if (or (eq value eof) (< pos (length string)))
              nil
              value))
        (error () nil))))

  (defun runtime-command--alist-value (alist key &optional default)
    (if (and (listp alist) (every #'consp alist))
      (let* ((pair (assoc key alist :test #'string=)))
        (if pair (cdr pair) default))
      default))

  (defun runtime-command--render-summary (value)
    (with-output-to-string (s)
      (write value :stream s)))

  (defun runtime-command--emit-result (invocation-id command-id result &key diagnostics effects duration-ms)
    (runtime-bridge--emit-message
     "command.result"
     (list (cons "invocationId" invocation-id)
           (cons "commandId" command-id)
           (cons "result" result)
           (cons "effects" effects)
           (cons "diagnostics" (or diagnostics #()))
           (cons "durationMs" duration-ms))
     :request-id invocation-id
     :stream-id *runtime-command-stream-id*
     :error nil))

  (defun runtime-command--emit-error (invocation-id command-id phase summary &key retryable diagnostics)
    (runtime-bridge--emit-message
     "command.error"
     (list (cons "invocationId" invocation-id)
           (cons "commandId" command-id)
           (cons "phase" phase)
           (cons "retryable" (if retryable t nil))
           (cons "condition"
                 (list (cons "type" "simple-error")
                       (cons "summary" summary)
                       (cons "presentationId" nil)))
           (cons "diagnostics" (or diagnostics #())))
     :request-id invocation-id
     :stream-id *runtime-command-stream-id*
     :error nil))

  (defun runtime-command--eval-form (args context)
    (declare (ignore context))
    (let* ((form-string (runtime-command--alist-value args "form" nil)))
      (unless (and (stringp form-string) (> (length form-string) 0))
        (error "runtime.eval.form requires args.form string"))
      (let* ((read (runtime-command--safe-read-form form-string)))
        (when (null read)
          (error "runtime.eval.form could not read form"))
        (let* ((values (toplevel-eval read)))
          (when values
            (toplevel-print values))
          (list (cons "valueSummary"
                      (if values
                        (runtime-command--render-summary (car values))
                        "NIL"))
                (cons "valuesCount" (length values)))))))

  (defun runtime-command--inspect-presentation (args)
    (let* ((presentation-id (runtime-command--alist-value args "presentationId" nil)))
      (list (cons "presentationId" presentation-id)
            (cons "valueSummary"
                  (if presentation-id
                    (format nil "inspect ~a" presentation-id)
                    "inspect")))))

  (defun runtime-command--restart-id (restart index)
    (let* ((name (ignore-errors (restart-name restart))))
      (if name
        (format nil "rst-~a-~d" (string-downcase (string name)) index)
        (format nil "rst-~d" index))))

  (defun runtime-command--collect-restarts (&optional condition)
    (let* ((source (or condition *runtime-debugger-current-condition* *break-condition*))
           (restarts (ignore-errors (compute-restarts source)))
           (index 0)
           (items nil))
      (dolist (restart restarts (nreverse items))
        (let* ((id (runtime-command--restart-id restart index))
               (name (ignore-errors (restart-name restart)))
               (title (if name
                        (string-capitalize (string-downcase (string name)))
                        (format nil "Restart ~d" (1+ index))))
               (description (ignore-errors (with-output-to-string (s) (princ restart s))))
               (recommended (and name (string= (string-downcase (string name)) "continue")))
               (recommended-reason (if recommended "Continue the current operation." nil))
               (json (list (cons "id" id)
                           (cons "title" title)
                           (cons "description" (or description title))
                           (cons "safety" "safe")
                           (cons "argSchema" #())
                           (cons "preview" nil)
                           (cons "recommended" (if recommended t nil))
                           (cons "recommendedReason" recommended-reason))))
          (push (list :id id :restart restart :json json) items))
        (incf index))))

  (defun runtime-command--condition-summary (&optional condition)
    (let* ((source (or condition *runtime-debugger-current-condition* *break-condition*)))
      (if source
        (format nil "~a" source)
        "No active debugger condition")))

  (defun runtime-command--build-debugger-snapshot (&key condition error-id task-id)
    (let* ((source (or condition *runtime-debugger-current-condition* *break-condition*))
           (resolved-error-id
            (or error-id
                *runtime-debugger-current-error-id*
                (format nil "err-~d" (incf *runtime-debugger-error-counter*))))
           (summary (runtime-command--condition-summary source))
           (restart-entries (runtime-command--collect-restarts source))
           (restart-json (coerce (mapcar (lambda (entry) (getf entry :json)) restart-entries) 'vector))
           (section (vector (list (cons "id" "sec-what")
                                  (cons "title" "What happened")
                                  (cons "text" summary))))
           (condition-json (list (cons "id" resolved-error-id)
                                 (cons "kind" "error")
                                 (cons "message" summary)
                                 (cons "summary" summary)
                                 (cons "sections" section))))
      (list (cons "errorId" resolved-error-id)
            (cons "taskId" task-id)
            (cons "condition" condition-json)
            (cons "frames" #())
            (cons "restarts" restart-json)
            (cons "selectedFrameId" nil))))

  (defun runtime-bridge-emit-debugger-snapshot (&key condition error-id task-id request-id)
    (when *runtime-bridge-enabled*
      (let* ((payload (runtime-command--build-debugger-snapshot
                       :condition condition
                       :error-id error-id
                       :task-id task-id))
             (resolved-error-id (cdr (assoc "errorId" payload :test #'string=))))
        (setf *runtime-debugger-current-error-id* resolved-error-id
              *runtime-debugger-current-condition* (or condition *runtime-debugger-current-condition* *break-condition*))
        (runtime-bridge--emit-message
         "debugger.snapshot"
         payload
         :request-id request-id
         :stream-id "debugger"
         :error nil)
        payload)))

  (defun runtime-command--find-restart-entry (restart-id &optional condition)
    (find restart-id
          (runtime-command--collect-restarts condition)
          :test #'string=
          :key (lambda (entry) (getf entry :id))))

  (defun runtime-command--open-debugger (args context)
    (declare (ignore args context))
    (let* ((payload (runtime-bridge-emit-debugger-snapshot
                     :condition *runtime-debugger-current-condition*
                     :error-id *runtime-debugger-current-error-id*)))
      (list (cons "errorId" (cdr (assoc "errorId" payload :test #'string=)))
            (cons "status" "snapshot-emitted"))))

  (defun runtime-command--invoke-restart (args context)
    (declare (ignore context))
    (let* ((restart-id (runtime-command--alist-value args "restartId" nil))
           (error-id (runtime-command--alist-value args "errorId" nil))
           (entry (and (stringp restart-id)
                       (runtime-command--find-restart-entry restart-id *runtime-debugger-current-condition*))))
      (unless (and (stringp restart-id) (> (length restart-id) 0))
        (error "runtime.restart.invoke requires args.restartId"))
      (unless entry
        (error "Unknown restart id: ~a" restart-id))
      (let* ((restart-json (getf entry :json))
             (summary (format nil "Restart ~a requested" restart-id)))
        (runtime-bridge--emit-message
         "debugger.restart"
         (list (cons "type" "invoked")
               (cons "errorId" (or error-id *runtime-debugger-current-error-id*))
               (cons "restartId" restart-id)
               (cons "summary" summary)
               (cons "restart" restart-json))
         :request-id nil
         :stream-id "debugger"
         :error nil)
        (list (cons "restartOutcome"
                    (list (cons "errorId" (or error-id *runtime-debugger-current-error-id*))
                          (cons "restartId" restart-id)
                          (cons "status" "requested")
                          (cons "summary" summary)))))))

  (defun runtime-command--dispatch (frame)
    (let* ((invocation-id (getf frame :invocation-id))
           (command-id (getf frame :command-id))
           (args (runtime-command--safe-read-form (getf frame :args-form-string)))
           (context (runtime-command--safe-read-form (getf frame :context-form-string)))
           (start-ms (runtime-bridge--now-ms)))
      (unless (and (stringp invocation-id) (> (length invocation-id) 0))
        (return-from runtime-command--dispatch nil))
      (unless (and (stringp command-id) (> (length command-id) 0))
        (runtime-command--emit-error invocation-id "unknown" "dispatch" "Missing command id" :retryable nil)
        (return-from runtime-command--dispatch nil))
      (handler-case
          (let* ((result
                  (cond
                    ((string= command-id "runtime.eval.form")
                     (runtime-command--eval-form args context))
                    ((string= command-id "runtime.recording.rerun")
                     (runtime-command--eval-form args context))
                    ((string= command-id "runtime.restart.invoke")
                     (runtime-command--invoke-restart args context))
                    ((string= command-id "runtime.debugger.open")
                     (runtime-command--open-debugger args context))
                    ((string= command-id "runtime.inspect.presentation")
                     (runtime-command--inspect-presentation args))
                    (t
                     (error "Unknown runtime command: ~a" command-id))))
                 (duration-ms (- (runtime-bridge--now-ms) start-ms)))
            (runtime-command--emit-result invocation-id command-id result :duration-ms duration-ms))
        (error (condition)
          (runtime-command--emit-error invocation-id
                                       command-id
                                       "execute"
                                       (format nil "~a" condition)
                                       :retryable t))))
    t)

  (defun runtime-command--poll-frame (&key (max-bytes +runtime-command-max-bytes+) (allow-pending nil))
    (let* ((buffer (make-array max-bytes :element-type '(unsigned-byte 8)))
           (flags (if allow-pending 1 0)))
      (ccl:rlet ((out-len :unsigned-long))
        (let* ((r (ccl:with-pointer-to-ivector (ptr buffer)
                    (ccl:external-call "wasm_kernel_runtime_command_poll"
                                       :unsigned-long max-bytes
                                       :unsigned-long flags
                                       :address ptr
                                       :unsigned-long max-bytes
                                       :address out-len
                                       :signed-long))))
          (cond
            ((< r 0) (values nil r))
            ((= r 0) (values nil 0))
            (t
             (let* ((n (ccl:pref out-len :unsigned-long))
                    (bytes (if (and n (> n 0))
                             (let ((copy (make-array n :element-type '(unsigned-byte 8))))
                               (replace copy buffer :end2 n)
                               copy)
                             (make-array 0 :element-type '(unsigned-byte 8)))))
               (values bytes r))))))))

  (defun runtime-bridge-pump-commands (&key (max-commands 4))
    (when (and *runtime-bridge-enabled* *runtime-command-enabled*)
      (loop repeat max-commands do
        (multiple-value-bind (bytes status) (runtime-command--poll-frame)
          (declare (ignore status))
          (when (null bytes)
            (return))
          (let* ((frame (runtime-command--decode-frame bytes)))
            (when frame
              (runtime-command--dispatch frame))))))
    nil)

  (defun runtime-bridge-emit-output (values)
    (when (and *runtime-bridge-enabled* values)
      (ignore-errors
        (runtime-bridge--emit-json (runtime-bridge--encode-output values)))))))


(defun toplevel-print (values &optional (out *standard-output*))
  (setq /// // // / / values)
  (unless (eq (car values) (%unbound-marker))
    (setq *** ** ** * *  (%car values)))
  (when values
    (fresh-line out)
    (dolist (val values) (write val :stream out) (terpri out))
    (runtime-bridge-emit-output values)))

(defparameter *listener-prompt-format* "~[?~:;~:*~d >~] ")

  
(defun print-listener-prompt (stream &optional (force t))
  (unless *quiet-flag*
    (when (or force (neq *break-level* *last-break-level*))
      (let* ((*listener-indent* nil))
        (fresh-line stream)
        (format stream *listener-prompt-format* *break-level*))
      (setq *last-break-level* *break-level*)))
    (force-output stream))


;;; Fairly crude default error-handlingbehavior, and a fairly crude mechanism
;;; for customizing it.

(defvar *app-error-handler-mode* :quit
  "one of :quit, :quit-quietly, :listener might be useful.")

(defmethod application-error ((a application) condition error-pointer)
  (case *app-error-handler-mode*
    (:listener   (break-loop-handle-error condition error-pointer))
    (:quit-quietly (quit -1))
    (:quit  (format t "~&Fatal error in ~s : ~a"
                    (pathname-name (car *command-line-argument-list*))
                    condition)
                    (quit -1))))

(defun make-application-error-handler (app mode)
  (declare (ignore app))
  (setq *app-error-handler-mode* mode))


; You may want to do this anyway even if your application
; does not otherwise wish to be a "lisp-development-system"
(defmethod application-error ((a lisp-development-system) condition error-pointer)
  (break-loop-handle-error condition error-pointer))

(defun abnormal-application-exit ()
  (ignore-errors
    (print-call-history)
    (write-line (lisp-implementation-version) *debug-io*)
    (force-output *debug-io*)
    (quit -1))
  #+wasm32-target
  (error "abnormal-application-exit is not supported on wasm")
  #-wasm32-target
  (#__exit -1))

;; Make these available to debugger hook
(defvar *top-error-frame* nil)
(defvar *break-loop-type* nil) ;; e.g. "Debug", "Signal", "Error".

(defun break-loop-handle-error (condition *top-error-frame*)
  (multiple-value-bind (bogus-globals newvals oldvals) (%check-error-globals)
    (dolist (x bogus-globals)
      (set x (funcall (pop newvals))))
    (let ((msg (if *batch-flag* ;; Give a little more info if exiting
                 (format nil "Error of type ~s" (type-of condition))
                 "Error")))
      (when (and *debugger-hook* *break-on-errors* (not *batch-flag*))
        (let ((hook *debugger-hook*)
              (*debugger-hook* nil)
              (*break-loop-type* msg))
          (funcall hook condition hook)))
      #+wasm32-target
      (when *runtime-bridge-enabled*
        (setf *runtime-debugger-current-condition* condition
              *runtime-debugger-current-error-id* (format nil "err-~d" (incf *runtime-debugger-error-counter*)))
        (ignore-errors
          (runtime-bridge-emit-debugger-snapshot
           :condition condition
           :error-id *runtime-debugger-current-error-id*)))
      (%break-message msg condition))
    (let* ((s *error-output*))
      (dolist (bogusness bogus-globals)
        (let ((oldval (pop oldvals)))
          (format s "~&;  NOTE: ~S was " bogusness)
          (if (eq oldval (%unbound-marker-8))
            (format s "unbound")
            (format s "~s" oldval))
          (format s ", was reset to ~s ." (symbol-value bogusness)))))
    (if (and *break-on-errors* (not *batch-flag*))
      (break-loop condition)
      (if *batch-flag*
        (abnormal-application-exit)
        (abort)))))

(defun break (&optional string &rest args)
  "Print a message and invoke the debugger without allowing any possibility
   of condition handling occurring."
  (if *batch-flag*
    (apply #'error (or string "BREAK invoked in batch mode") args)
    (apply #'%break-in-frame (%get-frame-ptr) string args)))

(defun %break-in-frame (fp &optional string &rest args)
  (flet ((do-break-loop ()
           (let ((c (if (typep string 'condition)
                      string
                      (make-condition 'simple-condition
                                    :format-control (or string "")
                                    :format-arguments args))))
             (cbreak-loop "Break" "Return from BREAK." c fp))))
    (cond ((%i> *interrupt-level* -1)
           (do-break-loop))
          (*break-loop-when-uninterruptable*
           (format *error-output* "Break while interrupt-level less than zero; binding to 0 during break-loop.")
           (let ((interrupt-level (interrupt-level)))
	     (unwind-protect
		  (progn
		    (setf (interrupt-level) 0)
		    (do-break-loop))
	       (setf (interrupt-level) interrupt-level))))
          (t (format *error-output* "Break while interrupt-level less than zero; ignored.")))))


(defun invoke-debugger (condition &aux (*top-error-frame* (%get-frame-ptr)))
  "Enter the debugger."
  (let ((c (require-type condition 'condition))
        (msg "Debug"))
    (when *debugger-hook*
      (let ((hook *debugger-hook*)
            (*debugger-hook* nil)
            (*break-loop-type* msg))
        (funcall hook c hook)))
    (%break-message msg c)
    (break-loop c)))

(defvar *show-condition-context* t
  "The type of conditions which should include the execution context as part of their error-output message.
   E.g. value of 'error will prevent warnings from including the calling function and process in the warning message")

(defun %break-message (msg condition &optional (error-pointer *top-error-frame*) (prefixchar #\>))
  (let ((*print-circle* *error-print-circle*)
        ;(*print-prett*y nil)
        (*print-array* nil)
        (*print-escape* t)
        (*print-gensym* t)
        (*print-length* (default-print-length *error-print-length*))
        (*print-level* (default-print-level *error-print-level*))
        (*print-string-length* (default-print-string-length *error-print-string-length*))
        (*print-lines* nil)
        (*print-miser-width* nil)
        (*print-readably* nil)
        (*print-right-margin* nil)
        (*signal-printing-errors* nil)
        (s (make-indenting-string-output-stream prefixchar nil))
        (sub (make-string-output-stream))
        (show-context (typep condition *show-condition-context*))
        (indent 0))
    (format s "~A~@[ ~A:~] " prefixchar msg)
    (setf (indenting-string-output-stream-indent s) (setq indent (column s)))
    (decf (stream-line-length sub) indent)
    ;(format s "~A" condition) ; evil if circle
    (report-condition condition sub)
    (format s "~A" (get-output-stream-string sub))
    (if (and show-context
             (not (and (typep condition 'simple-program-error)
                       (simple-program-error-context condition))))
      (format *error-output* "~&~A~%~A While executing: ~S"
              (get-output-stream-string s) prefixchar (%real-err-fn-name error-pointer))
      (format *error-output* "~&~A"
              (get-output-stream-string s)))
    (when show-context
      (if *current-process*
        (format *error-output* ", in process ~a(~d).~%" (process-name *current-process*) (process-serial-number *current-process*))
        (format *error-output* ", in an uninitialized process~%")))
  (force-output *error-output*)))
					; returns NIL

(defvar *break-hook* nil)

(defun cbreak-loop (msg cont-string condition *top-error-frame*)
  (let* ((*print-readably* nil)
         (hook *break-hook*))
    (restart-case (progn
                    (when (and (eq (type-of condition) 'simple-condition)
                               (equal (simple-condition-format-control condition) ""))
                      (setq condition (make-condition 'simple-condition
                                        :format-control "~a"
                                        :format-arguments (list msg))))
                    (when hook
                      (let ((*break-hook* nil)
                            (*break-loop-type* msg))
                        (funcall hook condition hook))
                      (setq hook nil))
                    (%break-message msg condition)
                    (break-loop condition))
      (continue () :report (lambda (stream) (write-string cont-string stream))))
    (unless hook
      (fresh-line *error-output*))
    nil))

(defun warn (condition-or-format-string &rest args)
  "Warn about a situation by signalling a condition formed by DATUM and
   ARGUMENTS. While the condition is being signaled, a MUFFLE-WARNING restart
   exists that causes WARN to immediately return NIL."
  (when (typep condition-or-format-string 'condition)
    (unless (typep condition-or-format-string 'warning)
      (report-bad-arg condition-or-format-string 'warning))
    (when args
      (error 'type-error :datum args :expected-type 'null
	     :format-control "Extra arguments in ~s.")))
  (let ((fp (%get-frame-ptr))
        (c (require-type (condition-arg condition-or-format-string args 'simple-warning) 'warning)))
    (when *break-on-warnings*
      (cbreak-loop "Warning" "Signal the warning." c fp))
    (restart-case (signal c)
      (muffle-warning () :report "Skip the warning" (return-from warn nil)))
    (%break-message (if (typep c 'compiler-warning) "Compiler warning" "Warning") c fp #\;)
    ))

(defmacro new-backtrace-info (dialog youngest oldest tcr condition current fake db-link level)
  (let* ((cond (gensym)))
  `(let* ((,cond ,condition))
    (vector ,dialog ,youngest ,oldest ,tcr (cons nil (compute-restarts ,cond)) (%catch-top ,tcr) ,cond ,current ,fake ,db-link ,level))))

(defmethod backtrace-context-continuable-p ((context vector))
  (not (null (find 'continue (cdr (bt.restarts context)) :key #'restart-name))))

(defmethod backtrace-context-break-level ((context vector))
  (bt.break-level context))

(defmethod backtrace-context-restarts ((context vector))
  (cdr (bt.restarts context)))


;;; Each of these stack ranges defines the entire range of (control/value/temp)
;;; addresses; they can be used to addresses of stack-allocated objects
;;; for printing.
#-(or arm-target wasm32-target)
(defun make-tsp-stack-range (tcr bt-info)
  (list (cons (%catch-tsp (bt.top-catch bt-info))
              (%fixnum-ref (%fixnum-ref tcr target::tcr.ts-area)
                                target::area.high))))

#+ppc-target
(defun make-vsp-stack-range (tcr bt-info)
  (list (cons (%fixnum-ref
               (%svref (bt.top-catch bt-info) target::catch-frame.csp-cell)
               target::lisp-frame.savevsp)
              (%fixnum-ref (%fixnum-ref tcr target::tcr.vs-area) target::area.high))))
#+x8632-target
(defun make-vsp-stack-range (tcr bt-info)
  (list (cons (%svref (bt.top-catch bt-info) target::catch-frame.esp-cell)
              (%fixnum-ref
               (%fixnum-ref tcr (- target::tcr.vs-area target::tcr-bias))
               target::area.high))))

#+x8664-target
(defun make-vsp-stack-range (tcr bt-info)
  (list (cons (%svref (bt.top-catch bt-info) target::catch-frame.rsp-cell)
              (%fixnum-ref (%fixnum-ref tcr target::tcr.vs-area) target::area.high))))

#+arm-target 
(defun make-vsp-stack-range (tcr bt-info)
  (list (cons (%fixnum-ref (catch-frame-sp (bt.top-catch bt-info)) target::lisp-frame.savevsp)
              (%fixnum-ref (%fixnum-ref tcr target::tcr.vs-area) target::area.high))))

#+ppc-target
(defun make-csp-stack-range (tcr bt-info)
  (list (cons (%svref (bt.top-catch bt-info) target::catch-frame.csp-cell)
              (%fixnum-ref (%fixnum-ref tcr target::tcr.cs-area) target::area.high))))

#+x8632-target
(defun make-csp-stack-range (tcr bt-info)
  (let ((cs-area nil))
    #+windows-target
    (let ((aux (%fixnum-ref tcr (- target::tcr.aux target::tcr-bias))))
      (setq cs-area (%fixnum-ref aux target::tcr-aux.cs-area)))
    #-windows-target
    (setq cs-area (%fixnum-ref tcr target::tcr.cs-area))
  (list (cons (%svref (bt.top-catch bt-info) target::catch-frame.foreign-sp-cell)
              (%fixnum-ref cs-area target::area.high)))))

#+x8664-target
(defun make-csp-stack-range (tcr bt-info)
  (list (cons (%svref (bt.top-catch bt-info) target::catch-frame.foreign-sp-cell)
              (%fixnum-ref (%fixnum-ref tcr target::tcr.cs-area) target::area.high))))

#+arm-target
(defun make-csp-stack-range (tcr bt-info)
  (list (cons (catch-frame-sp (bt.top-catch bt-info))
              (%fixnum-ref (%fixnum-ref tcr target::tcr.cs-area) target::area.high))))



(declaim (notinline select-backtrace))

(defun select-backtrace ()
  (declare (notinline select-backtrace))
  ;(require 'new-backtrace)
  (require :inspector)
  (select-backtrace))

(defvar *break-condition* nil "condition argument to innermost break-loop.")
(defvar *break-frame* nil "frame-pointer arg to break-loop")
(defvar *break-loop-when-uninterruptable* t)
(defvar *show-restarts-on-break* nil)
(defvar *show-available-restarts* nil)

(defvar *error-reentry-count* 0)

(defun funcall-with-error-reentry-detection (thunk)
  (let* ((count *error-reentry-count*)
         (*error-reentry-count* (1+ count)))
    (cond ((eql count 0) (funcall thunk))
          ((eql count 1) (error "Error reporting error"))
          (t (bug "Error reporting error")))))


(defvar %last-continue% nil)
(defun break-loop (condition &optional (frame-pointer *top-error-frame*))
  "Never returns"
  (let* ((%handlers% (last %handlers%)) ; firewall
         (*break-frame* frame-pointer)
         (*break-condition* condition)
         (*compiling-file* nil)
         (*backquote-stack* nil)
         (continue (find-restart 'continue))
         (*continuablep* (unless (eq %last-continue% continue) continue))
         (%last-continue% continue)
         (*standard-input* *debug-io*)
         (*standard-output* *debug-io*)
         (*signal-printing-errors* nil)
         (*read-suppress* nil)
         (*print-readably* nil)
	 (context (new-backtrace-info nil
                                      frame-pointer
                                      (if *backtrace-contexts*
                                        (or (child-frame
                                             (bt.youngest (car *backtrace-contexts*))
                                             nil)
                                            (last-frame-ptr))
                                        (last-frame-ptr))
                                      (%current-tcr)
                                      condition
                                      (%current-frame-ptr)
                                      #+ppc-target *fake-stack-frames*
                                      #+x86-target (%current-frame-ptr)
                                      #+arm-target (or (current-fake-stack-frame) (%current-frame-ptr))
                                      #+wasm32-target nil
                                      (db-link)
                                      (1+ *break-level*)))
         (*default-integer-command* `(:c 0 ,(1- (length (cdr (bt.restarts context))))))
         (*backtrace-contexts* (cons context *backtrace-contexts*)))
    (with-terminal-input
      (with-toplevel-commands :break
        (if *continuablep*
          (let* ((*print-circle* *error-print-circle*)
                 (*print-length* (default-print-length *error-print-length*))
                 (*print-level* (default-print-level *error-print-level*))
                 (*print-string-length* (default-print-string-length *error-print-string-length*))
                 ;(*print-pretty* nil)
                 (*print-array* nil))
            (format t (or (application-ui-operation *application* :break-options-string t)
                          "~&> Type :GO to continue, :POP to abort, :R for a list of available restarts."))
            (format t "~&> If continued: ~A~%" continue))
          (format t (or (application-ui-operation *application* :break-options-string nil)
                        "~&> Type :POP to abort, :R for a list of available restarts.~%")))
        (format t "~&> Type :? for other options.")
        (terpri)
        (force-output)

        (clear-input *debug-io*)
        (setq *error-reentry-count* 0)  ; succesfully reported error
        (ignoring-without-interrupts
          (unwind-protect
               (progn
                 (application-ui-operation *application*
                                           :enter-backtrace-context context)
                 (run-read-loop :break-level (1+ *break-level*)
                                :input-stream *debug-io*
                                :output-stream *debug-io*))
            (application-ui-operation *application* :exit-backtrace-context
                                      context)))))))



(defun display-restarts (&optional (condition *break-condition*))
  (loop
    for restart in (compute-restarts condition)
    for count upfrom 0
    do (format *debug-io* "~&~D. ~A" count restart)
    finally (fresh-line *debug-io*)))

(defun select-restart (n &optional (condition *break-condition*))
  (let* ((restarts (compute-restarts condition)))
    (invoke-restart-interactively
     (nth (require-type n `(integer 0 (,(length restarts)))) restarts))))




; End of l1-readloop-lds.lisp
