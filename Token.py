tokens_list = {}


from InstaBear import StoryBear,PostBear
class Token:
    def __init__(self,res=None,pool=None,token=None):
        if not res or not pool:
            self.token = token
            self.token = None
            self.session = None
            self.id = None
            self.interval = None
            return
        self.token = res['token']
        self.session = res['session_id']
        self.id = res['id']
        self.interval = res['interval']
        config = {
        'username':self.token,
        'interval':self.interval,
            'cookies':{
                'ds_user_id':self.id,
                'sessionid':self.session
            }
        }
        self.storybear = StoryBear.Bear(config,pool)
        self.postbear = PostBear.PostBear(self.storybear,pool)