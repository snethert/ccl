
;;; Wasm file-provider protocol values. Providers translate host results into
;;; this domain; these are not acquired from a native interface database.
(cl:defconstant io-seek-set 0)
(cl:defconstant io-seek-cur 1)
(cl:defconstant io-error-interrupted 4)
(cl:defconstant io-error-file-exists 17)
(cl:defconstant io-error-system-file-limit 23)
(cl:defconstant io-error-process-file-limit 24)
