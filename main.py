#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
from google.appengine.ext import ndb
from google.appengine.api import search
import logging
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images
import markdown2
jinja_environment = jinja2.Environment(autoescape=False, loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

class Bank(ndb.Model):
    question = ndb.TextProperty(required=True)
    answer = ndb.TextProperty(required=True)
    ans_img_url = ndb.StringProperty(required=False)    
    branch = ndb.StringProperty(required=True)
    semester = ndb.StringProperty(required=True)
    subject = ndb.StringProperty(required=True)
    year = ndb.StringProperty(required=True)
    chapter = ndb.StringProperty(required=True)
    qno=ndb.StringProperty(required=True)
    part=ndb.StringProperty(required=True)
    marks=ndb.IntegerProperty(required=True)

class SearchHandler(webapp2.RequestHandler):  
    
    def get(self):
    	try:
    	    search_string=self.request.get('q')#get search info
    	    if search_string.strip()!="":
                result=search.Index(name="VTUQ").search(search_string)
                template = jinja_environment.get_template('search.html')
                context = {'results':result, 'markup':markdown2.markdown, 'query': search_string}           
                html = template.render(context)
                self.response.write(html)
            else:
                context = {'results':'', 'markup':markdown2.markdown, 'query': search_string}
                template = jinja_environment.get_template('search.html')
                html = template.render(context)
                self.response.write(html)
                

	except search.Error:
            logging.exception('search failed')
            context = {'results':'', 'markup':markdown2.markdown, 'query': search_string}
            template = jinja_environment.get_template('search.html')
            html = template.render(context)
            self.response.write(html)
            
        	    



def create_document(bank):
    tags=bank.branch+','+bank.semester+','+bank.subject+','+bank.year+','+bank.chapter+','+bank.qno+','+bank.part+','+str(bank.marks)
    new_doc=search.Document(doc_id=str(bank.key.id()),fields = [search.TextField(name='ques',value=bank.question), search.TextField(name='ans',value=bank.answer),search.TextField(name='tags',value=tags)])
    return new_doc

class FormHandler(blobstore_handlers.BlobstoreUploadHandler):
    def get(self):    	
        template = jinja_environment.get_template('form.html')
        upload_url = blobstore.create_upload_url('/dataentry')
        context = {'url':upload_url}
        html = template.render(context)
        self.response.write(html)

    def post(self): 
        q=self.request.get("question")
        #q=markdown2.markdown(q,extras=["wiki-tables"])
        a=self.request.get("answer")
        #a=markdown2.markdown(a,extras=["wiki-tables"])
        logging.warning('answer>>>: \n'+a)
        branch=self.request.get("branch")
        semester=self.request.get("semester")
        subject=self.request.get("subject")
        year=self.request.get("year") 
        chapter=self.request.get("chapter")
        qno=self.request.get("qno") 
        part=self.request.get("part").upper()
        marks=int(self.request.get("marks"))
        try:
        	upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
    		blob_info = upload_files[0]  
    		ans_img_url=images.get_serving_url(blob_info.key()) 
    	except:
    		ans_img_url=""	     
        bank=Bank(question=q,answer=a,branch=branch,semester=semester,subject=subject,year=year,chapter=chapter, ans_img_url=ans_img_url,qno=qno,part=part, marks=marks)
        item= bank
        bank.put()

        doc = create_document(bank)      
        try:
            search.Index(name='VTUQ').put(doc)
          
        except search.Error:
            logging.exception('Add failed')
        upload_url = blobstore.create_upload_url('/dataentry')
        template = jinja_environment.get_template('form.html')
        context = {'item':item,'img_url':ans_img_url,'url': upload_url}
        html = template.render(context)
        self.response.write(html)

class ItemHandler(webapp2.RequestHandler):
    def get(self, item_id):
        item = Bank.get_by_id(int(item_id))
        #item.question=markdown2.markdown(item.question,extras=["wiki-tables"])
        context = {'item': item, 'markup':markdown2.markdown}
        template = jinja_environment.get_template('item.html')
        html = template.render(context)
        self.response.write(html)

class PaperHandler(webapp2.RequestHandler):
    def get(self):
        branch=self.request.get("branch")
        semester=self.request.get("semester")
        subject=self.request.get("subject")
        year=self.request.get("year")
        chapter=self.request.get("chapter")
        query_object = Bank.query()
        top_100 = query_object.filter(Bank.branch==branch).filter(Bank.semester==semester).filter(Bank.subject==subject).filter(Bank.year==year).filter(Bank.chapter==chapter)
        top_100_partA = top_100.filter(Bank.part=='A').fetch(100)
        top_100_partB = top_100.filter(Bank.part=='B').fetch(100)     
        top_100_partA.sort(key = lambda x: x.qno)
        top_100_partB.sort(key = lambda x: x.qno)
        context = {'itemsA': top_100_partA, 'itemsB': top_100_partB, 'markup':markdown2.markdown}
        template = jinja_environment.get_template('paper.html')
        html = template.render(context)
        self.response.write(html)
   
class EditItemHandler(webapp2.RequestHandler):
    def get(self,item_id):
        item = Bank.get_by_id(int(item_id))   
        upload_url = blobstore.create_upload_url('/edit_item/'+item_id)
        context = {'url':upload_url}    
        context = {'item': item, 'url': upload_url}
        template = jinja_environment.get_template('form.html')
        html = template.render(context)
        self.response.write(html)

    def post(self,item_id):
    	# some saaf safayi
        item = Bank.get_by_id(int(item_id))
        ans_img_url=item.ans_img_url # old image url
        item.key.delete()       
        doc_index = search.Index(name='VTUQ')
        doc_index.delete(str(item_id))    
        #  TODO: Delete the image blob object in an asynchronous way so that we don't keep orphaned images eating up memory space. Low priority! Disk is cheap.      
        
        q=self.request.get("question") 
        a=self.request.get("answer")
        branch=self.request.get("branch")
        semester=self.request.get("semester")
        subject=self.request.get("subject")
        year=self.request.get("year") 
        chapter=self.request.get("chapter")
        qno=self.request.get("qno") 
        part=self.request.get("part").upper()
        marks=int(self.request.get("marks"))
        try:
            upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
            blob_info = upload_files[0]  
            ans_img_url=images.get_serving_url(blob_info.key()) 
    	except:
    	    pass # old image url is retained     
        bank=Bank(question=q,answer=a,branch=branch,semester=semester,subject=subject,year=year,chapter=chapter, ans_img_url=ans_img_url,qno=qno,part=part, marks=marks)
       
        new_item_key=bank.put()
        new_item_id=new_item_key.id()
        doc = create_document(bank)      
        try:
            search.Index(name='VTUQ').put(doc)
          
        except search.Error:
            logging.exception('Add failed')
        context = {'item': bank}
        self.redirect('/edit_item/'+str(new_item_id))


            
app = webapp2.WSGIApplication([
    ('/dataentry', FormHandler),
    ('/item/(?P<item_id>.*)', ItemHandler),
    ('/', SearchHandler),('/paper',PaperHandler), ('/edit_item/(?P<item_id>.*)',EditItemHandler)
    
], debug=True)
