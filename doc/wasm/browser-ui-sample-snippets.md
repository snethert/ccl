## Browser UI Sample Snippets (Revised)

Status: Draft

This document provides representative UI snippets for building different kinds of tools on the browser CCL UI toolkit. The snippets are intentionally small and focus on patterns: tasks, windows, presentations, commands, Canvas/WebGL views, and inspectable state. They are examples, not a full application.

## 1. A Devtools Workspace Task (REPL + Inspector + Editor)

```lisp
(defclass devtools-task ()
  ((id      :initarg :id :reader task-id)
   (title   :initarg :title :accessor task-title)))

(defmethod ui:task-default-windows ((t devtools-task))
  (list (make-instance 'repl-window :task t)
        (make-instance 'inspector-window :task t)
        (make-instance 'editor-window :task t)))

(ui:defcommand devtools.layout-default
  (:doc "Apply the default devtools layout.")
  (:exec (lambda (ctx)
           (ui:apply-layout
            ctx
            (ui:layout
             (ui:split-horizontal
              (ui:tab-group :id 'left-pane :windows '(repl-window inspector-window))
              (ui:tab-group :id 'right-pane :windows '(editor-window))
              :ratio 0.35))))))
```

## 2. Command Palette (Centralized Commands)

```lisp
(defclass command-palette-model ()
  ((query :initform "" :accessor palette-query)))

(defmethod ui:list-count ((m command-palette-model))
  (length (ui:commands-matching (palette-query m))))

(defmethod ui:list-item ((m command-palette-model) i)
  (nth i (ui:commands-matching (palette-query m))))

(defmethod ui:list-activate ((m command-palette-model) i)
  (ui:execute-command (ui:command-id (ui:list-item m i))))

(defmethod ui:window-view ((w command-palette-window))
  (let ((m (make-instance 'command-palette-model)))
    (ui:vbox
     (ui:text-field :label "Command" :model (ui:text-model m :slot 'query))
     (ui:list-view :model m))))
```

## 3. Inspector Window (Object-Centric UI)

```lisp
(defclass inspector-window ()
  ((task   :initarg :task :reader window-task)
   (object :initarg :object :accessor inspector-object)))

(defmethod ui:window-view ((w inspector-window))
  (ui:vbox
   (ui:header "Inspector")
   (ui:object-view :object (inspector-object w))
   (ui:tree-view :model (ui:object-tree-model (inspector-object w)))))

(ui:defcommand system.inspect-selection
  (:doc "Inspect the current selection.")
  (:enabled (lambda (ctx)
              (if (ui:selection ctx)
                  (values t nil)
                  (values nil "Nothing selected."))))
  (:exec (lambda (ctx)
           (ui:open-window
            (make-instance 'inspector-window
                           :task (ui:current-task ctx)
                           :object (ui:selection ctx))
            :focus t))))
```

## 4. Debugger Window (Restarts Are First-Class)

```lisp
(defclass debugger-window ()
  ((task      :initarg :task :reader window-task)
   (condition :initarg :condition :reader dbg-condition)
   (stack     :initarg :stack :reader dbg-stack)
   (restarts  :initarg :restarts :reader dbg-restarts)))

(defmethod ui:window-view ((w debugger-window))
  (ui:vbox
   (ui:header "Debugger")
   (ui:panel (ui:object-view :object (dbg-condition w)))
   (ui:panel (ui:stack-view :frames (dbg-stack w)))
   (ui:panel (ui:restart-list :restarts (dbg-restarts w)))))
```

## 5. Presentation + Translator (Semantic Interaction)

```lisp
(ui:defpresentation issue
  (:type issue)
  (:render (lambda (issue)
             (ui:hbox
              (ui:icon :name (if (issue-open-p issue) "open" "closed"))
              (ui:label :text (issue-title issue))))))

(ui:deftranslator issue.open
  (:from issue :gesture :primary-click)
  (:to-command 'issue.open))

(ui:deftranslator issue.inspect
  (:from issue :gesture :alt-click)
  (:to-command 'system.inspect-selection))
```

## 6. Diagram Editor (Canvas View + Hit Testing)

```lisp
(defclass diagram-model ()
  ((nodes :initform nil :accessor diagram-nodes)
   (links :initform nil :accessor diagram-links)
   (selection :initform nil :accessor diagram-selection)))

(defmethod ui:window-view ((w diagram-window))
  (let ((m (diagram-model (window-task w))))
    (ui:vbox
     (ui:toolbar
      (ui:button :label "New Node" :command 'diagram.new-node))
     (ui:canvas-view
      :id 'diagram-canvas
      :model m
      :render #'diagram-render
      :hit-test #'diagram-hit-test))))

(defun diagram-render (m ctx)
  (ui:draw-grid ctx)
  (dolist (n (diagram-nodes m))
    (ui:draw-rect ctx (node-bounds n)
                  :fill (if (eq n (diagram-selection m)) :accent :panel))
    (ui:draw-text ctx (node-title n) (node-title-pos n)))
  (dolist (l (diagram-links m))
    (ui:draw-line ctx (link-start l) (link-end l))))

(defun diagram-hit-test (m x y)
  (find-if (lambda (n) (point-in-rect-p x y (node-bounds n)))
           (diagram-nodes m)))

(ui:defcommand diagram.new-node
  (:exec (lambda (ctx)
           (let ((m (diagram-model (ui:current-task ctx))))
             (push (make-node :title "New" :pos (random-pos)) (diagram-nodes m))
             (ui:invalidate m)))))
```

## 7. Timeline Viewer (Canvas + Commands)

```lisp
(defclass timeline-model ()
  ((events :initform nil :accessor timeline-events)
   (selection :initform nil :accessor timeline-selection)))

(defmethod ui:window-view ((w timeline-window))
  (ui:canvas-view
   :id 'timeline
   :model (timeline-model (window-task w))
   :render #'timeline-render
   :hit-test #'timeline-hit-test))

(defun timeline-render (m ctx)
  (dolist (e (timeline-events m))
    (ui:draw-bar ctx (event-bounds e)
                 :fill (if (eq e (timeline-selection m)) :accent :muted))))
```

## 8. Log Viewer (Virtualized Table)

```lisp
(defclass log-model ()
  ((rows :initform #() :accessor log-rows)
   (selection :initform nil :accessor log-selection)))

(defmethod ui:table-row-count ((m log-model))
  (length (log-rows m)))

(defmethod ui:table-row ((m log-model) i)
  (aref (log-rows m) i))

(defmethod ui:window-view ((w log-window))
  (ui:table-view :model (log-model (window-task w)) :virtualized t))
```

## 9. Mixed DOM + Canvas Composition

```lisp
(defmethod ui:window-view ((w profiler-window))
  (ui:split-horizontal
   (ui:tree-view :model (profile-tree (window-task w)))
   (ui:canvas-view :model (profile-flamegraph (window-task w))
                   :render #'flamegraph-render
                   :hit-test #'flamegraph-hit-test)
   :ratio 0.3))
```

## 10. Background Jobs and Progress

```lisp
(defclass compile-job ()
  ((task :initarg :task :reader job-task)
   (progress :initform 0 :accessor job-progress)))

(defmethod ui:job-run ((j compile-job))
  (compile-all (job-task j)
               :on-progress (lambda (p)
                              (setf (job-progress j) p)
                              (ui:invalidate (job-task j)))))

(defmethod ui:window-view ((w build-window))
  (ui:vbox
   (ui:progress-bar :value (job-progress (current-job (window-task w))))
   (ui:log-view :model (build-log (window-task w)))))
```

## 11. Rapid UI Construction (Builder Output Shape)

```lisp
(ui:quick-window
 :task task
 :title "Quick Scratch"
 :content (ui:vbox
           (ui:label :text "Scratchpad")
           (ui:text-area :model (scratch-model task))
           (ui:hbox
            (ui:button :label "Run" :command 'scratch.run)
            (ui:button :label "Clear" :command 'scratch.clear))))
```

## Notes
- Commands are the only way to mutate UI state; widgets request commands, they do not directly change global state.
- Presentations enable object-aware interaction and command discovery.
- Canvas/WebGL views participate in hit-testing, focus, and command routing via stable IDs.
- Layout modifications are commands that update the persistent layout tree.
- Errors are surfaced via debugger windows with restarts, not modal alerts.
