from quart import Quart,request,make_response,redirect
from quart.json import jsonify
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart.templating import render_template
from asyncio import sleep,Lock,get_event_loop
from base64 import b64encode
from json import loads,dumps
from aiomysql.cursors import DictCursor
from pymysql.err import OperationalError
from InstaBear import queries

class MyQuart(Quart):
    jinja_options = Quart.jinja_options.copy()
    jinja_options.update(dict(variable_start_string='%%', variable_end_string='%%',))

class WebClient:
    def __init__(self,pool,bind):
        self.app = MyQuart(__name__,template_folder='templates/',static_folder='static/',static_url_path='/static')
        self.pool = pool
        self.bind = [bind]
        self.lock = Lock()
        #self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    async def init(self):
        self.conn = await self.pool.acquire()
        self.db = await self.conn.cursor(DictCursor)
        from Token import tokens_list,Token

        async def session(req):
            token = req.args['token'] if 'token' in req.args else req.cookies['bear_token'] if 'bear_token' in req.cookies else None
            rt = {'valid':0,'admin':0,'token':token}
            if token:
                async with self.lock:
                    while True:
                        try:
                            await self.db.execute("SELECT * FROM tokens WHERE token=%s",(token,))
                            res = await self.db.fetchone()
                            break
                        except OperationalError:
                            self.conn = await self.pool.acquire()
                            self.db = await self.conn.cursor(DictCursor)
                            continue
                rt = {**rt, **res}
                if rt['valid']:
                    if token in tokens_list:
                        rt['token'] = tokens_list[token]
                    else:
                        t = Token(token=token)
                        rt['token'] = t
                        tokens_list[token] = t
                    return rt
            return 0


        @self.app.route("/")
        async def home():
            v = await session(request)
            if not v:
                return await render_template("error.html",error_code=403,error_msg="Δεν δόθηκε κωδικός πρόσβασης ή μη έγκυρος κωδικός πρόσβασης"),403
            async with self.lock:
                await self.db.execute("""
                SELECT  
                    (SELECT COUNT(*) FROM users) users,
                    (SELECT COUNT(*) FROM stories) AS stories,
                    (SELECT COUNT(*) FROM posts) AS posts
                """)
                counts = await self.db.fetchone()
            async with self.lock:
                await self.db.execute("SELECT stories.id,stories.uploaded,users.name,users.current_pfp,stories.ext FROM stories INNER JOIN users ON stories.user_id=users.id WHERE users.account=%s ORDER BY uploaded DESC LIMIT 1",(v['token'].token))
                l_story = await self.db.fetchone()
            if v['token'].storybear:
                user_id = await v['token'].storybear.check_auth()
            return await render_template("home_new.html",
            story_count=counts['stories'],
            post_count=counts['posts'],
            user_count=counts['users'],
            ls_name=l_story['name'] if l_story else None,
            ls_pfp=l_story['current_pfp'] if l_story else None,
            ls_id=l_story['id'] if l_story else None,
            ls_timestamp=l_story['uploaded'] if l_story else None,
            ls_ext=l_story['ext'] if l_story else None,
            logged_in=(bool(await v['token'].storybear.check_auth()) if v['token'].storybear else False),
            user_id=user_id
            ),200,{'Set-Cookie':'bear_token={}; Max-Age=2147483647'.format(v['token'].token)}
        
        @self.app.route("/search",methods=["POST","GET"])
        async def search():
            v = await session(request)
            username = self.conn.escape((await request.form).get("username"))
            account = self.conn.escape((await request.form).get("account"))
            c = 1
            sql="SELECT stories.uploaded,stories.id,users.name,users.current_pfp,stories.ext,stories.user_id,users.scrape_posts FROM stories INNER JOIN users ON stories.user_id = users.id WHERE users.account='{}'".format(v['token'].token)
            if username and len(username)>2:
                sql = sql+" AND name={}".format(username) if c>0 else sql+"name={}".format(username)
                c+=1
            if account and len(account)>2:
                sql = sql+" AND account={}".format(account) if c>0 else sql+"account={}".format(account)
                c+=1
            async with self.lock:
                await self.db.execute(sql)
                res = await self.db.fetchall()
            if not res:
                return jsonify({'message':'No stories found'}),404
            else:
                for i,v in enumerate(res):
                    res[i]['id'] = str(v['id']) 
                res = jsonify(res)
                return res
        
        @self.app.route("/story/<sid>")
        async def story_media(sid):
            v = await session(request)
            async with self.lock:
                await self.db.execute("SELECT stories.media,stories.ext FROM stories INNER join users ON users.id=stories.user_id WHERE stories.id=%s AND users.account=%s",(sid,v['token'].token,))
                res = await self.db.fetchone()
            if res:
                ctype = "image/jpeg" if res['ext']=='jpg' else "video/mp4" if res['ext']=='mp4' else "application/octet-stream"
                media = res['media']
                ln = len(res['media'])
                response = await make_response(media)
                response.timeout = None
                response.headers = {"Content-Disposition":"inline","Content-Type":ctype,"Content-Length":str(ln),'Cache-Control':'max-age=31556926'}
                return response
            else:
                return '',404

        @self.app.route("/usr_autoc")
        async def autoc():
            v = await session(request)
            usr = request.args.get("input")
            if len(usr)>=3:
                async with self.lock:
                    await self.db.execute("SELECT name FROM users WHERE name LIKE '{}' AND account='{}'".format("%{}%".format(usr),v['token'].token))
                    res = await self.db.fetchall()
                if res:
                    if len(res)>0:
                        return jsonify([i['name'] for i in res])
                    else:
                        return '[]',404
                else:
                    return '[]',404
            else:
                return '',400

        @self.app.route("/posts")
        async def posts():
            v = await session(request)
            if not v:
                return await render_template("error.html",error_code=403,error_msg="Δεν δόθηκε κωδικός πρόσβασης ή μη έγκυρος κωδικός πρόσβασης"),403
            usr = request.args.get("username")
            async with self.lock:
                await self.db.execute("SELECT posts.id,posts.shortcode,posts.caption,posts.ext,posts.timestamp FROM posts INNER join users ON users.id=posts.user_id WHERE posts.user_id=(SELECT id FROM users WHERE name=%s) AND users.account=%s",(usr,v['token'].token))
                res = await self.db.fetchall()
            if res:
                
                for i,v in enumerate(res):
                    res[i]['id'] = str(v['id'])
                return jsonify(res)
            else:
                return jsonify([]),404

        @self.app.route("/post/<pid>")
        async def post_media(pid):
            v = await session(request)
            if not v:
                return await render_template("error.html",error_code=403,error_msg="Δεν δόθηκε κωδικός πρόσβασης ή μη έγκυρος κωδικός πρόσβασης"),403
            async with self.lock:
                await self.db.execute("SELECT posts.media,posts.ext FROM posts INNER join users ON users.id=posts.user_id WHERE posts.id=%s AND users.account=%s",(pid,v['token'].token,))
                res = await self.db.fetchone()
            if res:
                ctype = "image/jpeg" if res['ext']=='jpg' else "video/mp4" if res['ext']=='mp4' else "application/octet-stream"
                media = res['media']
                ln = len(res['media'])
                response = await make_response(media)
                response.timeout = None
                response.headers = {"Content-Disposition":"inline","Content-Type":ctype,"Content-Length":str(ln),'Cache-Control':'max-age=31556926'}
                return response
            else:
                return '',404

        @self.app.route("/post_toggle")
        async def toggle_posts():
            v = await session(request)
            if not v:
                return await render_template("error.html",error_code=403,error_msg="Δεν δόθηκε κωδικός πρόσβασης ή μη έγκυρος κωδικός πρόσβασης"),403
            usr = self.conn.escape(request.args.get("username"))
            async with self.lock:
                await self.db.execute("""
                CASE WHEN ( (SELECT scrape_posts FROM users WHERE name={0} AND account='{1}') = 1 )
                    THEN UPDATE users SET scrape_posts=0 WHERE name={0};
                    SELECT 0;
                    ELSE UPDATE users SET scrape_posts=1 WHERE name={0};
                    SELECT 1;
                END CASE
                """.format(usr,v['token'].token))
                res = await self.db.fetchone()
            if res:
                return list(res)[0],200

        @self.app.route("/profile_pictures/<uid>")
        async def pfps(uid):
            v = await session(request)
            if not v:
                return await render_template("error.html",error_code=403,error_msg="Δεν δόθηκε κωδικός πρόσβασης ή μη έγκυρος κωδικός πρόσβασης"),403
            async with self.lock:
                await self.db.execute("SELECT profile_pictures.media,profile_pictures.timestamp FROM profile_pictures INNER JOIN users ON profile_pictures.user_id=users.id WHERE profile_pictures.user_id=%s AND users.account=%s",(uid,v['token'].token,))
                res = await self.db.fetchall()
            if res:
                for i,v in enumerate(res):
                    res[i]['media'] = b64encode(v['media']).decode("utf-8")
                return await render_template('profile_pictures.html',pfps=res)

        @self.app.route("/insta_login",methods=["POST"])
        async def i_login():
            v = await session(request)
            if not v:
                return await render_template("error.html",error_code=403,error_msg="Δεν δόθηκε κωδικός πρόσβασης ή μη έγκυρος κωδικός πρόσβασης"),403
            if v['token'].storybear:
                res = await v['token'].storybear.client.get(queries.HOME)
                csrf = ""
                if res.status==200:
                    cookies = v['token'].storybear.client.cookie_jar.filter_cookies(queries.HOME)
                    for k,value in cookies.items():
                        if k=="csrftoken":
                            csrf = value
                            break
                if not csrf:
                    return 'Login error',500 #TODO: Login error
                username = (await request.form).get("username")
                password = (await request.form).get("password")
                if not username or not password:
                    return 'Invalid login data',400
                res = await v['token'].storybear.client.post(queries.LOGIN,headers={'x-csrftoken':csrf.value},data={
                    'username':username,
                    'password':password
                })
                if res.status==200:
                    res = await res.json()
                    if res['authenticated']:
                        if 'userId' not in res:
                            cookies = v['token'].storybear.client.cookie_jar.filter_cookies(queries.HOME)
                            for k,value in cookies.items():
                                if k=="ds_user_id":
                                    user_id = value.value
                                    break
                        else:
                            user_id = res['userId']
                        session_id = ""
                        cookies = v['token'].storybear.client.cookie_jar.filter_cookies(queries.HOME)
                        for k,value in cookies.items():
                            if k=="sessionid":
                                session_id = value
                                break
                        print(session_id,user_id)
                        async with self.lock:
                            await self.db.execute("UPDATE tokens SET id=%s,session_id=%s WHERE token=%s",(user_id,session_id.value,v['token'].token))
                            v['token'].storybear.update_creds(session_id.value,user_id)
                            v['token'].postbear.update_creds(session_id.value,user_id)
                            return redirect("/")
                return await render_template('error.html',error_code=403,error_msg="Λάθος όνομα χρήστη ή κωδικός πρόσβασης")

      
        cfg = Config()
        cfg.bind = self.bind
        print("Starting server on {}".format(self.bind))
        return serve(self.app,cfg)

