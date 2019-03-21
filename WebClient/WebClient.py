from quart import Quart,request,make_response,redirect
from quart.json import jsonify
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart.templating import render_template
from asyncio import get_event_loop
from aiomysql.cursors import DictCursor
from base64 import b64encode

class MyQuart(Quart):
    jinja_options = Quart.jinja_options.copy()
    jinja_options.update(dict(variable_start_string='%%', variable_end_string='%%',))

class WebClient:
    def __init__(self,pool,bind):
        self.app = MyQuart(__name__,template_folder='templates/',static_folder='static/',static_url_path='/static')
        self.pool = pool
        self.bind = [bind]

    async def getDb(self):
        async with self.pool.acquire() as conn:
            return await conn.cursor(DictCursor)

    async def init(self):
        self.escape = (await self.pool.acquire()).escape

        async def session(req):
            db = await self.getDb()
            token = req.args['token'] if 'token' in req.args else req.cookies['bear_token'] if 'bear_token' in req.cookies else None
            if token:
                res = await db.execute("SELECT valid,admin FROM tokens WHERE token=%s",(token,))
                if res:
                    res = await db.fetchone()
                    if res['valid']:
                        if res['admin']:
                            return {'token':token,'admin':True,'db':db}
                    else:
                        return {'token':token,'admin':False,'db':db}
            return 0

        @self.app.route("/")
        async def home():
            v = await session(request)
            if not v:
                return await render_template("auth_error.html"),403
            s_count = p_count = u_count = 0
            res = await v['db'].execute("""
            SELECT  
                (SELECT COUNT(*) FROM users) users,
                (SELECT COUNT(*) FROM stories) AS stories,
                (SELECT COUNT(*) FROM posts) AS posts
            """)
            if res:
                res = await v['db'].fetchone()
                u_count = res['users']
                s_count = res['stories']
                p_count = res['posts']
            return await render_template("home.html",story_count=s_count,post_count=p_count,user_count=u_count),200,{'Set-Cookie':'bear_token={}; Max-Age=2147483647'.format(v['token'])},
        
        @self.app.route("/search",methods=["POST","GET"])
        async def search():
            v = await session(request)
            username = self.escape((await request.form).get("username"))
            account = self.escape((await request.form).get("account"))
            c = 0
            sql="SELECT stories.uploaded,stories.id,users.name,users.current_pfp,stories.ext,stories.user_id,users.scrape_posts FROM stories INNER JOIN users ON stories.user_id = users.id WHERE "
            if username and len(username)>2:
                sql = sql+" AND name={}".format(username) if c>0 else sql+"name={}".format(username)
                c+=1
            if account and len(account)>2:
                sql = sql+" AND account={}".format(account) if c>0 else sql+"account={}".format(account)
                c+=1
            res = await v['db'].execute(sql)
            if not res:
                return jsonify({'message':'No stories found'}),404
            else:
                res = await v['db'].fetchall()
                for i,v in enumerate(res):
                    res[i]['id'] = str(v['id']) 
                res = jsonify(res)
                return res
        
        @self.app.route("/story/<sid>")
        async def story_media(sid):
            v = await session(request)
            res = await v['db'].execute("SELECT media,ext FROM stories WHERE id=%s",(sid,))
            if res:
                res = await v['db'].fetchone()
                ctype = "image/jpeg" if res['ext']=='jpg' else "video/mp4" if res['ext']=='mp4' else "application/octet-stream"
                media = res['media']
                ln = len(res['media'])
                response = await make_response(media)
                response.timeout = None
                response.headers = {"Content-Disposition":"inline","Content-Type":ctype,"Content-Length":str(ln)}
                return response
            else:
                return '',404

        @self.app.route("/usr_autoc")
        async def autoc():
            v = await session(request)
            usr = request.args.get("input")
            if len(usr)>=3:
                res = await v['db'].execute("SELECT name FROM users WHERE name LIKE '{}'".format("%{}%".format(usr)))
                if res:
                    res = await v['db'].fetchall()
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
                return await render_template("auth_error.html")
            usr = request.args.get("username")
            res = await v['db'].execute("SELECT id,shortcode,caption,ext,timestamp FROM posts WHERE user_id=(SELECT id FROM users WHERE name=%s)",(usr,))
            if res:
                res = await v['db'].fetchall()
                for i,v in enumerate(res):
                    res[i]['id'] = str(v['id'])
                return jsonify(res)
            else:
                return jsonify([]),404

        @self.app.route("/post/<pid>")
        async def post_media(pid):
            v = await session(request)
            if not v:
                return await render_template("auth_error.html")
            res = await v['db'].execute("SELECT media,ext FROM posts WHERE id=%s",(pid,))
            if res:
                res = await v['db'].fetchone()
                ctype = "image/jpeg" if res['ext']=='jpg' else "video/mp4" if res['ext']=='mp4' else "application/octet-stream"
                media = res['media']
                ln = len(res['media'])
                response = await make_response(media)
                response.timeout = None
                response.headers = {"Content-Disposition":"inline","Content-Type":ctype,"Content-Length":str(ln)}
                return response
            else:
                return '',404

        @self.app.route("/post_toggle")
        async def toggle_posts():
            if not (await session(request))['admin']: return await render_template("admin_error.html"),403
            usr = self.escape(request.args.get("username"))
            res = await v['db'].execute("""
            CASE WHEN ( (SELECT scrape_posts FROM users WHERE name={0}) = 1 )
                THEN UPDATE users SET scrape_posts=0 WHERE name={0};
                SELECT 0;
                ELSE UPDATE users SET scrape_posts=1 WHERE name={0};
                SELECT 1;
            END CASE
            """.format(usr))
            if res:
                res = await v['db'].fetchone()
                return list(res)[0],200

        @self.app.route("/profile_pictures/<uid>")
        async def pfps(uid):
            v = await session(request)
            if not v:
                return await render_template("auth_error.html")
            res = await v['db'].execute("SELECT media,timestamp FROM profile_pictures WHERE user_id=%s",(uid,))
            if res:
                res = await v['db'].fetchall()
                for i,v in enumerate(res):
                    res[i]['media'] = b64encode(v['media']).decode("utf-8")
                return await render_template('profile_pictures.html',pfps=res)

        @self.app.route("/tokens")
        async def tokens():
            if not (await session(request))['admin']: return await render_template("admin_error.html"),403
            res = await v['db'].execute("SELECT * FROM tokens")
            if res:
                res = await v['db'].fetchall()
                return await render_template("tokens.html",tokens=res)

        @self.app.route("/make_admin/<token>")
        async def make_admin(token):
            if not (await session(request))['admin']: return await render_template("admin_error.html"),403
            res = await v['db'].execute("""
            CASE WHEN ( (SELECT admin FROM tokens WHERE token={0}) = 1 )
                THEN UPDATE tokens SET admin=0 WHERE token={0};
                ELSE UPDATE tokens SET admin=1 WHERE token={0};
            END CASE
            """.format(self.escape(token)))
            if res:
                return redirect("/tokens")

        @self.app.route("/validate_token/<token>")
        async def validate_token(token):
            if not (await session(request))['admin']: return await render_template("admin_error.html"),403
            res = await v['db'].execute("""
            CASE WHEN ( (SELECT valid FROM tokens WHERE token={0}) = 1 )
                THEN UPDATE tokens SET valid=0 WHERE token={0};
                ELSE UPDATE tokens SET valid=1 WHERE token={0};
            END CASE
            """.format(self.escape(token)))
            if res:
                return redirect("/tokens")

        cfg = Config()
        cfg.bind = self.bind
        print("Starting server on {}".format(self.bind))
        return serve(self.app,cfg)
