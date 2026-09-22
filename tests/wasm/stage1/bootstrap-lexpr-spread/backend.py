"""Lexpr spreading through the existing APPLY call protocol."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('condition_backend',HERE.parent/'bootstrap-condition-frontier/backend.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
base_generate=prior.generate
BACKEND=prior.BACKEND;ARCH=prior.ARCH;PACKET=prior.PACKET
CLASSES=prior.CLASSES
arch=prior.arch;runtime_files=prior.runtime_files;source_files=prior.source_files

def replace(s,a,b,count=1):
 assert s.count(a)==count,(a,s.count(a));return s.replace(a,b)

def generate():
 s=base_generate()
 s=replace(s,"(if (eq (third args) t) (b-apply (first args) (second args)) (refuse :b-spread-kind))",
  "(if (or (eq (third args) t) (and *bootstrap-front-end* (eql (third args) 0)))\n             (b-apply (first args) (second args) nil 0 (third args)) (refuse :b-spread-kind))")
 s=replace(s,"(if (eq spread t) (b-apply nil args self) (refuse :b-spread-kind))",
  "(if (or (eq spread t) (and *bootstrap-front-end* (eql spread 0)))\n                   (b-apply nil args self 0 spread) (refuse :b-spread-kind))")
 s=replace(s,'(defun b-apply (callee argument-list &optional local-self (ephemeral-bytes 0))',
  '(defun b-apply (callee argument-list &optional local-self (ephemeral-bytes 0) (spread-kind t))')
 s=replace(s,'(b-internal-apply callee argument-list local-self)))','(b-internal-apply callee argument-list local-self spread-kind)))')
 s=replace(s,'(defun b-internal-apply (callee argument-list local-self)',
  '(defun b-internal-apply (callee argument-list local-self &optional (spread-kind t))')
 start=s.index('(defun b-apply ');end=s.index(';;; Logical callable-object',start)
 part=s[start:end]
 begin='      ;; One cursor advances on every step'
 finish='      (write-string "(br $list_check)))" s)'
 for i in range(2):
  at=part.index(begin);stop=part.index(finish,at)+len(finish)
  old=part[at:stop]
  part=part[:at]+'''      (if (eql spread-kind 0)
        (write-string (bootstrap-lexpr-count (b-local cursor) length) s)
        (progn
'''+old.replace(begin,'      ;; Ordinary list spread: one cursor advances on every step')+'))'+part[stop:]
 search_from=0
 for dest,offset in [('base',16),('context',48)]:
  begin='      (format s "(block $spread_done'
  at=part.index(begin,search_from);stop=part.index('index index)',at)+len('index index)')
  old=part[at:stop]
  part=part[:at]+f'''      (if (eql spread-kind 0)
        (write-string (bootstrap-lexpr-copy cursor length index n {dest} {offset}) s)
'''+old+')'+part[stop:]
  search_from=at+len(old)+200
 s=s[:start]+part+s[end:]
 return s+'\n'+(HERE/'lexpr.lisp').read_text()

def proposal(src,out):
 prior.generate=generate
 return prior.proposal(src,out)
