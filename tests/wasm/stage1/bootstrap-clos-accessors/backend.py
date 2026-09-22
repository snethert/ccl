"""Reuse the lexpr proposal unchanged; this unit adds callers and inputs only."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lexpr_backend',HERE.parent/'bootstrap-lexpr-spread/backend.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
BACKEND=prior.BACKEND;ARCH=prior.ARCH;PACKET=prior.PACKET
CLASSES=prior.CLASSES
generate=prior.generate;arch=prior.arch;source_files=prior.source_files
runtime_files=prior.runtime_files;proposal=prior.proposal
