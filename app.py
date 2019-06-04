from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,validators,PasswordField,IntegerField
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.url_map.strict_slashes = False

app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']='viv@2298'
app.config['MYSQL_DB']='myflaskapp'
app.config['MYSQL_CURSORCLASS']='DictCursor'

mysql=MySQL(app)

hostelid=""

@app.route('/')
def index():
	return render_template('home.html')

#register user
class RegisterForm(Form):
	name=StringField('Name',[validators.Length(min=1,max=100)])
	roll_no=StringField('Roll No',[validators.Length(min=1,max=20)])
	email=StringField('Email',[validators.Length(min=1,max=50)])
	password=PasswordField('Password',[
		validators.DataRequired(),
		validators.EqualTo('confirm',message='Passwords do not match')
	])
	confirm=PasswordField('Confirm Password')	

@app.route('/register',methods=['GET','POST'])
def register():
	form=RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name=form.name.data
		roll_no=form.roll_no.data
		email=form.email.data
		password=sha256_crypt.encrypt(str(form.password.data))
		
		cur=mysql.connection.cursor()
		result=cur.execute("SELECT * FROM users WHERE email=%s",[email])
		result2=result=cur.execute("SELECT * FROM users WHERE roll_no=%s",[roll_no])
		if result>0 or result2>0:
			flash('Email already in use','warning')
			cur.close()
			redirect(url_for('register'))
		else:	
			cur.execute("INSERT INTO users(name,roll_no,email,password) VALUES(%s,%s,%s,%s)",(name,roll_no,email,password))

			mysql.connection.commit()
			cur.close()

			flash('You are now registered and can log in','success')
			
			return redirect(url_for('index'))	
	return render_template('register.html',form=form)	
username=""
useremail=""
userroll_no=""

#user login
@app.route('/login',methods=['GET','POST'])
def login():
	if request.method=='POST':
		roll_no=request.form['roll_no']
		password_candidate=request.form['password']

		#create cursor
		cur=mysql.connection.cursor()
		#get user by roll_no
		result=cur.execute("SELECT * FROM users WHERE roll_no=%s",[roll_no])

		if result>0:
			#get first user with that roll_no
			data=cur.fetchone()
			password=data['password']

			#compare passwords
			if sha256_crypt.verify(password_candidate,password):
				#passed
				session['logged_in']=True
				session['roll_no']=roll_no
				session['name']=data['name']
				session['email']=data['email']
				global username,useremail,userroll_no
				username=data['name']
				useremail = data['email']
				userroll_no =data['roll_no']
				flash('You are now logged in','success')
				return redirect(url_for('dashboard'))

			else:
				error='Invalid Login'
				return render_template('login.html',error=error)
			#close connection	
			cur.close()	
		else:
			error='Roll No not found'
			return render_template('login.html',error=error)

	return render_template('login.html')

#check if user logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args,**kwargs):
		if 'logged_in' in session:
			return f(*args,**kwargs)
		else:
			flash('Unauthorised,Please login','danger')
			return redirect(url_for('login'))	
	return wrap	

#log out
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out','success')
	return redirect(url_for('login'))

#dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
	#create cursor
	cur=mysql.connection.cursor()
	#get articles 
	result=cur.execute("SELECT * FROM articles")
	articles=cur.fetchall()
	if result>0:
		return render_template('dashboard.html',articles=articles)
	else:
		msg='No Articles Found'
		return render_template('dashboard.html',msg=msg)

	cur.close()

#articles
@app.route('/articles')
def articles():
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM articles")
	articles=cur.fetchall()
	if result>0:
		return render_template('articles.html',articles=articles)
	else:
		msg='No Articles Found'
		return render_template('articles.html',msg=msg)
	cur.close()

#single article
@app.route('/article/<string:id>/')
def article(id):
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM articles WHERE id=%s",[id])
	article=cur.fetchone()

	return render_template('article.html',article=article)		

#article form class
class ArticleForm(Form):
	title=StringField('Title',[validators.Length(min=1,max=200)])
	body=TextAreaField('Body',[validators.Length(min=1)])

#add article
@app.route('/add_article',methods=['GET','POST'])
@is_logged_in
def add_article():
	form=ArticleForm(request.form)
	if request.method =='POST' and form.validate():
		title=form.title.data
		body=form.body.data
		cur=mysql.connection.cursor()
		cur.execute("INSERT INTO articles(title,body,author) VALUES(%s,%s,%s)",(title,body,session['roll_no']))
		mysql.connection.commit()
		cur.close()

		flash('Article created','success')

		return redirect(url_for('dashboard'))

	return render_template('add_article.html',form=form)	

#edit article
@app.route('/edit_article/<string:id>',methods=['GET','POST'])
@is_logged_in
def edit_article(id):
	#crate cursor
	cur=mysql.connection.cursor()
	#get article by id
	result=cur.execute("SELECT * FROM articles WHERE id=%s",[id])
	article=cur.fetchone()

	#get form
	form=ArticleForm(request.form)
	
	#populate article form fields
	form.title.data=article['title']
	form.body.data=article['body']

	if request.method =='POST' and form.validate():
		title=request.form['title']
		body=request.form['body']

		#create cursor
		cur=mysql.connection.cursor()
		app.logger.info(title)

		#execute
		cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s",(title,body,[id]))

		mysql.connection.commit()
		cur.close()

		flash('Article Updated','success')

		return redirect(url_for('dashboard'))

	return render_template('edit_article.html',form=form)

#delete article
@app.route('/delete_article/<string:id>',methods=['POST'])
@is_logged_in
def delete_article(id):
	#create cursor
	cur=mysql.connection.cursor()
	cur.execute("DELETE FROM articles WHERE id=%s",[id])
	mysql.connection.commit()
	cur.close()

	flash('Article Deleted','success')

	return redirect(url_for('dashboard'))

# hostelid=""

#register admin
class RegisterForm2(Form):
	admin_name=StringField('Admin Name',[validators.Length(min=1,max=100)])
	hostel_name=StringField('Hostel Name',[validators.Length(min=1,max=100)])
	admin_email=StringField('Admin Email',[validators.Length(min=1,max=100)])
	admin_password=PasswordField('Admin Password',[
		validators.DataRequired(),
		validators.EqualTo('confirm',message='Passwords do not match')
	])
	confirm=PasswordField('Confirm Password')	

@app.route('/admin_register',methods=['GET','POST'])
def admin_register():
	form=RegisterForm2(request.form)
	if request.method == 'POST' and form.validate():
		admin_name=form.admin_name.data
		hostel_name=form.hostel_name.data
		admin_email=form.admin_email.data
		admin_password=sha256_crypt.encrypt(str(form.admin_password.data))
		
		cur=mysql.connection.cursor()
		result=cur.execute("SELECT * FROM admins WHERE admin_email=%s",[admin_email])
		if result>0:
			flash('Email already in use','warning')
			cur.close()
			redirect(url_for('admin_register'))
		else:	
			result2=cur.execute("SELECT * FROM hostels WHERE hostel_name=%s",[hostel_name])
			
			if result2>0:
				data=cur.fetchone()
				global hostelid 
				hostelid=data['hostel_id']
				# print(data['hostel_id'])
				# print(hostelid+"\n")
				cur.execute("INSERT INTO admins(hostel_id,admin_name,admin_email,admin_password) VALUES(%s,%s,%s,%s)",(data['hostel_id'],admin_name,admin_email,admin_password))
			
			else:	
				cur.execute("INSERT INTO hostels(hostel_name) VALUES(%s)",(hostel_name,))
				temp=cur.execute("SELECT * FROM hostels WHERE hostel_name=%s",[hostel_name])
				data2=cur.fetchone()
				cur.execute("INSERT INTO admins(hostel_id,admin_name,admin_email,admin_password) VALUES(%s,%s,%s,%s)",(data2['hostel_id'],admin_name,admin_email,admin_password))

			mysql.connection.commit()

			flash('You are now registered as an admin and can log in','success')
			
			return redirect(url_for('index'))	
	return render_template('admin_register.html',form=form)

#admin login
@app.route('/admin_login',methods=['GET','POST'])
def admin_login():
	if request.method=='POST':
		admin_email=request.form['admin_email']
		password_admin=request.form['admin_password']

		#create cursor
		cur=mysql.connection.cursor()
		#get user by roll_no
		result=cur.execute("SELECT * FROM admins WHERE admin_email=%s",[admin_email])

		if result>0:
			#get first user with that admin_email
			data=cur.fetchone()
			password=data['admin_password']
			#compare passwords
			if sha256_crypt.verify(password_admin,password):
			#if password==password_admin:
				#passed
				session['logged_in2']=True
				session['admin_email']=admin_email

				flash('You are now logged in','success')
				# temp='/dashboard2/'+hostelid
				# print(temp)
				result2=cur.execute("SELECT * FROM admins WHERE admin_email=%s",[admin_email])
				data2=cur.fetchone()
				global hostelid
				hostelid=data2['hostel_id']
				print(hostelid)
				cur.close()
				return redirect('/dashboard2/'+str(hostelid))

			else:
				error='Invalid Login'
				cur.close()
				return render_template('admin_login.html',error=error)
			#close connection	
				
		else:
			error='Email not found'
			return render_template('admin_login.html',error=error)

	return render_template('admin_login.html')

#check if admin logged in
def is_logged_in2(f):
	@wraps(f)
	def wrap(*args,**kwargs):
		if 'logged_in2' in session:
			return f(*args,**kwargs)
		else:
			flash('Unauthorised,Please login','danger')
			return redirect(url_for('admin_login'))	
	return wrap	

#admin_log out
@app.route('/admin_logout')
@is_logged_in2
def admin_logout():
	session.clear()
	flash('You are now logged out','success')
	return redirect(url_for('admin_login'))	

#store in pending
@app.route('/pending/<string:hostel_id>')
@is_logged_in
def pending(hostel_id):
	cur=mysql.connection.cursor()
	cur.execute("INSERT INTO pending(hostel_id,name,roll_no,email) VALUES(%s,%s,%s,%s)",(hostel_id,username,userroll_no,useremail))
	mysql.connection.commit()
	cur.close()
	return redirect(url_for('dashboard'))

#dashboard2
@app.route('/dashboard2/<string:hostel_id>')
@is_logged_in2
def dashboard2(hostel_id):
		student2=[]
		students=[]
		cur=mysql.connection.cursor()
		result=cur.execute("SELECT * FROM pending WHERE hostel_id=%s",[hostel_id])
		if result>0:
			students=cur.fetchall()
		result2=cur.execute("SELECT * FROM accepted WHERE hostel_id=%s",[hostel_id])
		if result2>0:
			student2=cur.fetchall()
		cur.close()
		return render_template('student_info.html',students=students,student2=student2,hostel_id=hostel_id)		

#accept user
@app.route('/added/<string:hostel_id>/')
@is_logged_in2
def added(hostel_id):
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM pending WHERE hostel_id=%s",[hostel_id])
	if result>0:
		data=cur.fetchone()
		cur.execute("INSERT INTO accepted(roll_no,hostel_id) VALUES(%s,%s)",(data['roll_no'],hostel_id))
		mysql.connection.commit()
		cur.execute("DELETE FROM pending WHERE id=%s",[data['id']])
		mysql.connection.commit()
		cur.close()
	# print(hostelid)
		return redirect('/dashboard2/'+str(hostelid))

#delete user
@app.route('/deleted/<string:hostel_id>/')
@is_logged_in2
def deleted(hostel_id):
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM pending WHERE hostel_id=%s",[hostel_id])
	if result>0:
		data=cur.fetchone()
		cur.execute("DELETE FROM pending WHERE id=%s",[data['id']])
		mysql.connection.commit()
		cur.close()
		return redirect('/dashboard2/'+str(hostelid))

#hostel-info
@app.route('/hostel_info')
@is_logged_in
def hostel_info():
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM hostels")
	if result>0:
		hostels=cur.fetchall()
	cur.close()
	return render_template('hostel_info.html',hostels=hostels)

#choose group to add issue
@app.route('/choose_group')
@is_logged_in
def choose_group():
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM accepted WHERE roll_no =%s",(session['roll_no'],))
	if result>0:
		ids=cur.fetchall()
		cur.close()
		return render_template('choose_group.html',ids=ids)
	else:
		flash('Sorry, you are not a member of any group','warning')	
		return redirect(url_for('dashboard'))

#article form class
class ArticleForm2(Form):
	title=StringField('Title',[validators.Length(min=1,max=200)])
	body=TextAreaField('Body',[validators.Length(min=1)])

@app.route('/add_issues/<string:hostel_id>',methods=['GET','POST'])
@is_logged_in
def add_issues_user(hostel_id):
	form=ArticleForm2(request.form)
	if request.method =='POST' and form.validate():
		title=form.title.data
		body=form.body.data

		#create cursor
		cur=mysql.connection.cursor()

		#execute
		cur.execute("INSERT INTO issues(hostel_id,title,author,body) VALUES(%s,%s,%s,%s)",(hostel_id,title,session['roll_no'],body))
		mysql.connection.commit()
		cur.close()

		flash('Issue created','success')

		return redirect(url_for('dashboard'))

	return render_template('add_issue.html',form=form)			

#user issues
@app.route('/see_issues/<string:hostel_id>')
def see_issues(hostel_id):
	#create cursor
	cur=mysql.connection.cursor()
	#get articles 
	result=cur.execute("SELECT * FROM issues WHERE hostel_id=%s",[hostel_id])
	issues=cur.fetchall()
	result2=cur.execute("SELECT * FROM liked WHERE roll_no=%s",[session['roll_no']])
	list_likes=cur.fetchall()
	like_ids=[]
	cur.close()
	for items in list_likes:
		like_ids.append(items['issue_id'])
	if result>0:
		return render_template('see_issues.html',issues=issues,like_ids=like_ids)
	else:
		msg='No Issues Found'
		return render_template('see_issues.html',msg=msg)
	cur.close()

#admin issues
@app.route('/admin_issues/<string:hostel_id>')
def see_issues2(hostel_id):
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM issues WHERE hostel_id=%s",[hostel_id])
	issues=cur.fetchall()
	if result>0:
		return render_template('admin_issues.html',issues=issues)
	else:
		msg='No Issues Found'
		return render_template('admin_issues.html',msg=msg)
	cur.close()

#user_comment gets displayed 
@app.route('/see_issue/<string:id>')
def see_issue(id):
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM issues WHERE id=%s",[id])
	issue=cur.fetchone()
	result2=cur.execute("SELECT * FROM comments WHERE issue_id=%s",[id])
	comment_list=cur.fetchall()
	return render_template('see_issue.html',issue=issue,comment_list=comment_list)

#admin_comment gets displayed 
@app.route('/admin_see_issue/<string:id>')
def admin_see_issue(id):
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM issues WHERE id=%s",[id])
	issue=cur.fetchone()
	result2=cur.execute("SELECT * FROM comments WHERE issue_id=%s",[id])
	comment_list=cur.fetchall()
	return render_template('admin_see_issue.html',issue=issue,comment_list=comment_list)


#like a comment
@app.route('/like/<string:hid>/<string:iid>')
def like(hid,iid):
	cur=mysql.connection.cursor()
	cur.execute("INSERT INTO liked(issue_id,hostel_id,roll_no) VALUES(%s,%s,%s)",(iid,hid,session['roll_no']))
	result2=cur.execute("SELECT noOfLikes FROM issues WHERE id=%s",[iid])
	temp=cur.fetchone()
	if temp['noOfLikes'] is not None:
		temp2=int(temp['noOfLikes'])+1
	else:
		temp2=1
	cur.execute("UPDATE issues SET noOfLikes=%s WHERE id=%s AND hostel_id=%s",(temp2,iid,hid))
	mysql.connection.commit()
	cur.close()
	return redirect('/see_issues/'+str(hid))

#remove a like
@app.route('/remove_like/<string:hid>/<string:iid>')
def remove_like(hid,iid):
	cur=mysql.connection.cursor()
	cur.execute("DELETE FROM liked WHERE issue_id=%s",iid)
	result2=cur.execute("SELECT noOfLikes FROM issues WHERE id=%s",[iid])
	temp=cur.fetchone()	
	if temp['noOfLikes'] is not None:
		temp2=int(temp['noOfLikes'])-1
	else:
		temp2=0
	cur.execute("UPDATE issues SET noOfLikes=%s WHERE id=%s AND hostel_id=%s",(temp2,iid,hid))
	mysql.connection.commit()
	cur.close()
	return redirect('/see_issues/'+str(hid))	

#choose group to check issue
@app.route('/choose_group2')
@is_logged_in
def choose_group2():
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM accepted WHERE roll_no =%s",(session['roll_no'],))
	if result>0:
		ids=cur.fetchall()
		cur.close()
		return render_template('choose_group2.html',ids=ids)
	else:
		flash('Sorry, you are not a member of any group','warning')	
		return redirect(url_for('dashboard'))

#article form class for admin
class ArticleForm3(Form):
	title=StringField('Title',[validators.Length(min=1,max=200)])
	body=TextAreaField('Body',[validators.Length(min=1)])

#reply for admins
@app.route('/reply_issues/<string:hostel_id>',methods=['GET','POST'])
@is_logged_in2
def reply_issues(hostel_id):
		form=ArticleForm3(request.form)
		if request.method =='POST' and form.validate():
			title=form.title.data
			body=form.body.data

			#create cursor
			cur=mysql.connection.cursor()

			#execute
			cur.execute("INSERT INTO issues(hostel_id,title,author,body) VALUES(%s,%s,%s,%s)",(hostel_id,title,session['admin_email'],body))
			mysql.connection.commit()
			cur.close()

			flash('Reply generated','success')

			return redirect('/dashboard2/'+str(hostel_id))

		return render_template('add_reply.html',form=form)	

#article form class for user_viewer
class ArticleForm4(Form):
	body=TextAreaField('Body',[validators.Length(min=1)])

# user_viewer comments
@app.route('/viewer_reply/<string:id>',methods=['GET','POST'])
def viewer_reply(id):
		form=ArticleForm4(request.form)
		if request.method =='POST' and form.validate():
			body=form.body.data
			cur=mysql.connection.cursor()
			result=cur.execute("SELECT * FROM issues WHERE id=%s",[id])
			temp=cur.fetchone()
			cur.execute("INSERT INTO comments(issue_id,hostel_id,author,viewer,comment) VALUES(%s,%s,%s,%s,%s)",(id,temp['hostel_id'],temp['author'],session['roll_no'],body))
			mysql.connection.commit()
			cur.close()
			return redirect('/see_issue/'+str(id))

		return render_template('viewer_reply.html',form=form)

#article form class for admin_viewer
class ArticleForm5(Form):
	body=TextAreaField('Body',[validators.Length(min=1)])

# admin_viewer comments
@app.route('/admin_viewer_reply/<string:id>',methods=['GET','POST'])
def admin_viewer_reply(id):
		form=ArticleForm5(request.form)
		if request.method =='POST' and form.validate():
			body=form.body.data
			cur=mysql.connection.cursor()
			result=cur.execute("SELECT * FROM issues WHERE id=%s",[id])
			temp=cur.fetchone()
			cur.execute("INSERT INTO comments(issue_id,hostel_id,author,viewer,comment) VALUES(%s,%s,%s,%s,%s)",(id,temp['hostel_id'],temp['author'],session['admin_email'],body))
			mysql.connection.commit()
			cur.close()
			return redirect('/admin_see_issue/'+str(id))

		return render_template('admin_viewer_reply.html',form=form)

@app.route('/events')
def events():
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM hostels")
	if result>0:
		hostels=cur.fetchall()
	cur.close()
	return render_template('events.html',hostels=hostels)

@app.route('/see_events/<string:hostel_id>')
def specific_events(hostel_id):
	cur=mysql.connection.cursor()
	result=cur.execute("SELECT * FROM events WHERE hostel_id=%s",[hostel_id])
	temp=cur.fetchall()
	return render_template('specific_events.html',temp=temp)

class ArticleForm6(Form):
	hid=StringField('Hostel_id',[validators.Length(min=1)])
	title=StringField('Title',[validators.Length(min=1,max=200)])
	details=TextAreaField('Details',[validators.Length(min=1)])
	org_date=TextAreaField('Organising Date',[validators.Length(min=1)])
	location=TextAreaField('Location',[validators.Length(min=1)])
	img_link=TextAreaField('Image link',[validators.Length(min=1)])

# add events to particular group
@app.route('/add_event/<string:hostel_id>',methods=['GET','POST'])
def add_event(hostel_id):
		form=ArticleForm6(request.form)
		if request.method =='POST':
			hid=form.hid.data
			title=form.title.data
			details=form.details.data
			org_date=form.org_date.data
			location=form.location.data
			img_link=form.img_link.data
			cur=mysql.connection.cursor()
			cur.execute("INSERT INTO events(hostel_id,title,details,org_date,location,img_link) VALUES(%s,%s,%s,%s,%s,%s)",(hostel_id,title,details,org_date,location,img_link))
			mysql.connection.commit()
			cur.close()
			return redirect('/dashboard2/'+str(hostel_id))

		return render_template('add_event.html',form=form)

if __name__ == '__main__':
	app.secret_key='secret123'
	app.run(debug=True)