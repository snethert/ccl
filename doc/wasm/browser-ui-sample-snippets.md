## Browser UI Sample App Snippets

Status: Draft

This document provides representative UI code snippets for a sample application built on the browser CCL UI toolkit. The snippets illustrate the intended programming model: tasks, windows, declarative view trees, centralized commands, restart-based error handling, explicit focus, and persistent layout.

The sample app is a lightweight "Issue Tracker" task. The code uses hypothetical `ui:` and `model:` APIs consistent with the toolkit spec. These snippets are not a full app; they are a reference collection of patterns.

## 1. Task and Window Definitions

```lisp
(defclass issue-task ()
  ((id          :initarg :id :reader task-id)
   (title       :initarg :title :accessor task-title)
   (issues      :initform (make-array 0 :adjustable t :fill-pointer 0)
                :accessor task-issues)
   (selection   :initform nil :accessor task-selection)
   (focus       :initform nil :accessor task-focus)
   (jobs        :initform nil :accessor task-jobs)))

(defmethod ui:task-default-windows ((t issue-task))
  (list (make-instance 'issue-list-window :task t)
        (make-instance 'issue-detail-window :task t)))

(defclass issue-list-window ()
  ((task :initarg :task :reader window-task)))

(defmethod ui:window-title ((w issue-list-window))
  (format nil "Issues: ~a" (task-title (window-task w))))

(defclass issue-detail-window ()
  ((task :initarg :task :reader window-task)))

(defmethod ui:window-title ((w issue-detail-window))
  (format nil "Details: ~a" (task-title (window-task w))))
```

## 2. Declarative View Trees

```lisp
(defmethod ui:window-view ((w issue-list-window))
  (let* ((t (window-task w))
         (m (make-instance 'issue-list-model :task t)))
    (ui:vbox
     (ui:toolbar
      (ui:button :label "New"    :command 'issue.new)
      (ui:button :label "Open"   :command 'issue.open)
      (ui:button :label "Delete" :command 'issue.delete))
     (ui:list-view :model m)
     (ui:status-bar :items (issue-status-items t)))))

(defmethod ui:window-view ((w issue-detail-window))
  (let* ((t (window-task w))
         (sel (task-selection t)))
    (ui:vbox
     (ui:header (if sel (issue-title sel) "No Issue Selected"))
     (ui:split-vertical
      (ui:panel
       (ui:form
        (ui:text-field :label "Title"  :model (issue-title-model sel))
        (ui:text-area  :label "Body"   :model (issue-body-model sel))
        (ui:toggle     :label "Open"   :model (issue-open-model sel))))
      (ui:panel
       (ui:table-view :model (issue-event-model sel)))))))
```

## 3. List Model Protocol

```lisp
(defclass issue-list-model ()
  ((task :initarg :task :reader model-task)
   (selection :initform nil :accessor model-selection)))

(defmethod ui:list-count ((m issue-list-model))
  (length (task-issues (model-task m))))

(defmethod ui:list-item ((m issue-list-model) i)
  (aref (task-issues (model-task m)) i))

(defmethod ui:list-key ((m issue-list-model) i)
  (issue-id (ui:list-item m i)))

(defmethod ui:list-selection ((m issue-list-model))
  (model-selection m))

(defmethod ui:set-list-selection ((m issue-list-model) sel)
  (setf (model-selection m) sel)
  (setf (task-selection (model-task m)) sel))

(defmethod ui:list-activate ((m issue-list-model) i)
  (ui:execute-command 'issue.open :index i))
```

## 4. Commands with Enablement Reasons

```lisp
(ui:defcommand issue.open
  (:doc "Open the selected issue in the detail pane.")
  (:enabled (lambda (ctx)
              (if (ui:selection ctx)
                  (values t nil)
                  (values nil "No issue selected."))))
  (:exec (lambda (ctx)
           (let ((issue (ui:selection ctx)))
             (ui:focus-window (ui:window-by-id ctx 'issue-detail) :reason :command)
             (ui:invalidate issue)))))

(ui:defcommand issue.delete
  (:doc "Delete the selected issue.")
  (:enabled (lambda (ctx)
              (if (ui:selection ctx)
                  (values t nil)
                  (values nil "Nothing selected."))))
  (:exec (lambda (ctx)
           (let* ((t (ui:current-task ctx))
                  (issue (ui:selection ctx)))
             (ui:confirm
              :title "Delete issue?"
              :message (format nil "Delete ~a?" (issue-title issue))
              :on-confirm (lambda ()
                            (issue-delete t issue)
                            (ui:invalidate t)))))))
```

## 5. Keybinding Resolution (Centralized)

```lisp
(ui:defkeymap issue.global
  (:scope :global)
  (:bind "Cmd-N" 'issue.new)
  (:bind "Cmd-O" 'issue.open)
  (:bind "Cmd-Backspace" 'issue.delete))

(ui:defkeymap issue.list-context
  (:scope :context :context-id 'issue-list-view)
  (:bind "Enter" 'issue.open)
  (:bind "Delete" 'issue.delete))
```

## 6. Explicit Focus Transitions

```lisp
(ui:defcommand issue.focus-list
  (:doc "Focus the issue list.")
  (:exec (lambda (ctx)
           (ui:focus-widget
            (ui:find-widget ctx :id 'issue-list)
            :reason :command))))

(ui:defcommand issue.focus-detail
  (:doc "Focus the issue detail form.")
  (:exec (lambda (ctx)
           (ui:focus-widget
            (ui:find-widget ctx :id 'issue-title-field)
            :reason :command))))
```

## 7. Persistent Layout Commands

```lisp
(ui:defcommand issue.layout-default
  (:doc "Restore the default issue layout.")
  (:exec (lambda (ctx)
           (ui:apply-layout
            ctx
            (ui:layout
             (ui:split-horizontal
              (ui:tab-group :id 'left-pane :windows '(issue-list-window))
              (ui:tab-group :id 'right-pane :windows '(issue-detail-window))
              :ratio 0.35))))))
```

## 8. Background Jobs and Progress

```lisp
(ui:defcommand issue.sync
  (:doc "Sync issues from the server.")
  (:exec (lambda (ctx)
           (ui:enqueue-job
            ctx
            (make-instance 'issue-sync-job
                           :task (ui:current-task ctx))))) )

(defclass issue-sync-job ()
  ((task :initarg :task :reader job-task)
   (progress :initform 0 :accessor job-progress)))

(defmethod ui:job-run ((j issue-sync-job))
  (restart-case
      (progn
        (issue-sync (job-task j) :on-progress (lambda (p)
                                               (setf (job-progress j) p)
                                               (ui:invalidate (job-task j)))))
    (retry () :report "Retry" (ui:job-run j))
    (use-cache () :report "Use cached data" (issue-load-cache (job-task j)))
    (cancel () :report "Cancel" nil)))
```

## 9. Restart-Based Error Handling in Commands

```lisp
(ui:defcommand issue.import
  (:doc "Import issues from a file.")
  (:exec (lambda (ctx)
           (let ((t (ui:current-task ctx)))
             (restart-case
                 (issue-import t (ui:prompt-file "Import from"))
               (use-empty () :report "Use empty list" (issue-clear t))
               (retry () :report "Retry" (ui:execute-command 'issue.import))
               (cancel () :report "Cancel" nil))
             (ui:invalidate t)))))
```

## 10. System State Inspector Entry Point

```lisp
(ui:defcommand system.inspect-state
  (:doc "Open System State inspector.")
  (:exec (lambda (ctx)
           (ui:open-window
            (make-instance 'system-inspector-window
                           :state (ui:system-state ctx)
                           :task (ui:current-task ctx))
            :focus t))))
```

## 11. Disabled Reason Display

```lisp
(defmethod ui:render-button ((b ui:button) ctx)
  (multiple-value-bind (enabled reason)
      (ui:command-enabled-p (ui:button-command b) ctx)
    (ui:dom-button
     :label (ui:button-label b)
     :disabled (not enabled)
     :tooltip (or reason ""))))
```

## 12. Persisting Task and Layout State

```lisp
(defmethod ui:serialize-task ((t issue-task))
  (list :id (task-id t)
        :title (task-title t)
        :issues (serialize-issues (task-issues t))
        :selection (when (task-selection t)
                     (issue-id (task-selection t)))))

(defmethod ui:serialize-layout ((ctx ui:context))
  (ui:layout->plist (ui:current-layout ctx)))

(defmethod ui:restore-task ((data list))
  (let ((t (make-instance 'issue-task
                          :id (getf data :id)
                          :title (getf data :title))))
    (setf (task-issues t) (deserialize-issues (getf data :issues)))
    t))
```

## 13. Debugger Window Skeleton

```lisp
(defclass debugger-window ()
  ((task :initarg :task :reader window-task)
   (condition :initarg :condition :reader dbg-condition)
   (stack :initarg :stack :reader dbg-stack)
   (restarts :initarg :restarts :reader dbg-restarts)))

(defmethod ui:window-view ((w debugger-window))
  (ui:vbox
   (ui:header "Debugger")
   (ui:panel (ui:object-view :object (dbg-condition w)))
   (ui:panel (ui:stack-view :frames (dbg-stack w)))
   (ui:panel (ui:restart-list :restarts (dbg-restarts w)))))
```

## 14. Notifications and Status

```lisp
(defun issue-status-items (t)
  (list (ui:status-item :label (format nil "~a issues" (length (task-issues t))))
        (ui:status-item :label (format nil "Jobs: ~a" (length (task-jobs t))))))

(ui:defcommand issue.notify-sync-done
  (:doc "Notify when sync completes.")
  (:exec (lambda (ctx)
           (ui:notify :title "Sync" :message "Issue sync completed."))))
```

## Notes
- Commands are the only way to mutate UI state; widgets request commands, they do not directly change global state.
- Focus changes are always explicit and carry a reason code for debugging.
- Layout modifications are commands that update the persistent layout tree.
- Errors are surfaced via debugger windows with restarts, not modal alerts.

