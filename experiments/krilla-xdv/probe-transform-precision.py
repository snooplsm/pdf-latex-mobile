#!/usr/bin/env python3
"""Diagnostic only: substitute baseline placement to isolate matrix precision effects.

This is not a renderer implementation or a baseline-independent parity fix.
"""
from decimal import Decimal as D
from pathlib import Path
import json,re,subprocess
from pypdf import PdfReader,PdfWriter
from pypdf.generic import DecodedStreamObject,NameObject
from PIL import Image,ImageChops
root=Path(__file__).resolve().parents[2];source=root/'.build/pdf-page-check';out=root/'.build/transform-precision';out.mkdir(exist_ok=True)
def transforms(page):
 identity=[D(1),D(0),D(0),D(1),D(0),D(0)];matrix=identity;stack=[];result=[]
 for operands,op in page.get_contents().operations:
  if op==b'q':stack.append(matrix[:])
  elif op==b'Q':matrix=stack.pop()
  elif op==b'cm':
   a,b,c,d,e,f=matrix;g,h,i,j,k,l=[D(str(v)) for v in operands]
   matrix=[a*g+c*h,b*g+d*h,a*i+c*j,b*i+d*j,a*k+c*l+e,b*k+d*l+f]
  elif op==b'Do':result.append(matrix[:])
 return result
report=[]
for name in ('default','first','second','third'):
 baseline=PdfReader(source/(name+'-baseline.pdf'));candidate=PdfReader(source/(name+'-replacement.pdf'))
 matrices=transforms(baseline.pages[0]);assert len(matrices)==1
 data=candidate.pages[0].get_contents().get_data()
 pattern=rb'q ([\d.eE+\- ]+) cm/x0 Do'
 found=re.findall(pattern,data);assert len(found)==1
 replacement=' '.join(format(v,'f') for v in matrices[0]).encode()
 rewritten=re.sub(pattern,lambda _:b'q '+replacement+b' cm/x0 Do',data)
 writer=PdfWriter();writer.clone_document_from_reader(candidate)
 stream=DecodedStreamObject();stream.set_data(rewritten);writer.pages[0][NameObject('/Contents')]=writer._add_object(stream)
 pdf=out/(name+'.pdf');writer.write(pdf)
 subprocess.run(['pdftoppm','-r','144','-singlefile','-png',str(pdf),str(pdf.with_suffix(''))],check=True,capture_output=True)
 a=Image.open(source/(name+'-baseline.png')).convert('RGB');b=Image.open(pdf.with_suffix('.png')).convert('RGB')
 pixels=sum(v!=(0,0,0) for v in ImageChops.difference(a,b).get_flattened_data())
 report.append({'case':name,'candidate_matrix':found[0].decode(),'baseline_composed_matrix':replacement.decode(),'different_pixels_after_diagnostic_substitution':pixels})
 print(report[-1],flush=True)
(out/'result.json').write_text(json.dumps({'scope':__doc__,'results':report},indent=2)+'\n')
