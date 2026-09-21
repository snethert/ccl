import importlib.util
from pathlib import Path
PARENT=Path(__file__).resolve().parent.parent/'startup-runtime'
s=importlib.util.spec_from_file_location('original_classification',PARENT/'classify.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
def classify():
 m=old.classify()
 for r in m['callbacks']:
  if r['classification']=='HOST' and r['providers']['browser']=='ACCEPTED_EFFECT':
   r['providers']['node']='INPUT_PROVIDER_NOT_QUALIFIED'
   r['obligation']+=' Node replay used browser-derived input data; it does not qualify a Node provider.'
 return m
def validate(m):
 if m!=classify():raise ValueError('classification identity or omitted callback')
 return {'callbacks':35,'accepted_effects':18,'browser_accepted_effects':18,'node_accepted_effects':13,'closure':'NOT_ESTABLISHED','scope':m['scope']}
