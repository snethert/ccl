;;; -*- Mode: Lisp; Package: CCL -*-

(in-package "CCL")

(when (fboundp 'wasm-startup-truth-close-sink)
  (ignore-errors
    (wasm-startup-truth-close-sink)))

(values)
