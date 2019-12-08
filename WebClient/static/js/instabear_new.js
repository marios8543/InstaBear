// VIEW RENDERING ---------------------------------------------------------------------------
const app = new Vue({
    el: "#mainWrap",
    data: {
        current_view: "home",
        story_count: 0,
        post_count: 0,
        user_count: 0,
        logged_in:false,
        login_anyway:false,
        user_id:0,
        inputs: {
            username: "",
            suggestions: [],
        },
        latest_story: {
            user: {
                name: "",
                profile_pic: ""
            },
            id: "",
            timestamp: ""
        },
        show_meta: false,
        media_view: {
            post: false,
            is_video: false,
            story_count: 0,
            post_count: 0,
            story_index: 0,
            post_index: 0,
            src: "",
            user: {
                id: "",
                name: "",
                profile_pic: "",
            },
            meta: {
                timestamp: 0,
                id: "",
                caption: "",
                save_posts:false
            }
        },
        tokens: [],
        current_token: ""
    },
    methods: {
        register_autoc: function(itm) {
            this.inputs.username = itm;
            this.inputs.suggestions = [];
        },
        formatTimestamp: function(timestamp) {
            let ts = new Date(timestamp * 1000);
            return `${ts.getDate()}/${ts.getMonth()}/${ts.getFullYear()} ${ts.getHours()}:${ts.getMinutes()}`;
        },
        autoc: function(val) {
            if (val.length >= 3) {
              let _this = this;
                $.ajax({
                    type: "GET",
                    url: "usr_autoc",
                    data: {
                        'input': val
                    },
                    success: function (data) {
                        _this.inputs.suggestions = data;
                    },
                    dataType: "json"
                });
            }
            else this.inputs.suggestions = [];
        },
        togglePosts: function() {
            let _this = this;
            $.ajax({
                type: "GET",
                url: "post_toggle",
                data: {
                    'username': this.media_view.user.name
                },
                success: function (data) {
                    _this.media_view.meta.save_posts = parseInt(data)==1;
                },
                dataType: "html"
            }).fail(function (xhr, text, err) { alert(`${xhr.responseText}`); });
        },
        toggleView: function() {
            if (this.media_view.post) {
                this.media_view.post = false;
            }
            else {
                if (posts.length == 0) {
                    fetchPosts();
                    if (posts.length == 0) {
                        return;
                    }
                    else {
                        this.media_view.post = true;
                    }
                }
                else {
                    this.media_view.post = true;
                }
            }
            loadMedia();
        },
        search: function() {
            $.ajax({

                type: "POST",
                url: "search",
                data: {
                    'username': app.inputs.username,
                },
                success: function (data) {
                    stories = data;
                    app.media_view.story_count = data.length;
                    app.media_view.story_index = 0;
                    loadMedia();
                },
                dataType: "json"
            }).fail(function (xhr, text, err) { alert(`${text} - ${err}`) });
       },
       loadToken: function(token) {
         setCookie("bear_token",token,365);
         window.location.href = "/";
       }
    },
    mounted: function() {
      let store = localStorage;
      let current_token = getCookie('bear_token');
      this.current_token = current_token;
      if (store.getItem("tokens")==null) {
        store.setItem("tokens",`["${current_token}"]`);
        this.tokens = [current_token];
      }
      else {
        let tokens = JSON.parse(store.getItem("tokens"));
        if (!tokens.includes(current_token)) {
          tokens.push(current_token);
          store.setItem("tokens",JSON.stringify(tokens));
        }
        this.tokens = tokens;
      }
    }
});

var stories = [];
var posts = [];

function fetchPosts() {
    $.ajax({
        type: "GET",
        url: "posts",
        data: {
            'username': app.media_view.user.name
        },
        success: function (data) {
            posts = data;
            app.media_view.post_count = data.length;
            app.media_view.post_index = 0;
        },
        dataType: "json"
    });
}

function loadMedia() {
    app.current_view = "media_view";
    if (!app.media_view.post) {
        let story = stories[app.media_view.story_index];
        app.media_view.is_video = story.ext == "mp4";
        app.media_view.src = `story/${story.id}`;
        app.media_view.user.id = story.user_id;
        app.media_view.user.name = story.name;
        app.media_view.user.profile_pic = story.current_pfp;
        app.media_view.meta.timestamp = story.uploaded;
        app.media_view.meta.id = story.id;
        app.media_view.meta.caption = null;
        app.media_view.meta.save_posts = story.scrape_posts==1
    }
    else if (posts.length > 0) {
        let post = posts[app.media_view.post_index];
        app.media_view.is_video = post.ext == "mp4";
        app.media_view.src = `post/${post.id}`;
        app.media_view.meta.id = post.id;
        app.media_view.meta.timestamp = post.timestamp;
        app.media_view.meta.caption = post.caption;
    }
}

// CONTROLS --------------------------------------------------------------

const hamm = new Hammer(document.getElementById("mainWrap"));
hamm.get('swipe').set({ direction: Hammer.DIRECTION_HORIZONTAL });

function previous() {
    if (app.current_view != "media_view") return
    if (app.media_view.post) {
        if (app.media_view.post_index - 1 >= 0) app.media_view.post_index--;
        else app.media_view.post_index = app.media_view.post_count - 1;
    }
    else {
        if (app.media_view.story_index - 1 >= 0) app.media_view.story_index--;
        else app.media_view.story_index = app.media_view.story_count - 1;
    }
    loadMedia();
}

function next() {
    if (app.current_view != "media_view") return
    if (app.media_view.post) {
        if (app.media_view.post_index + 1 < app.media_view.post_count) app.media_view.post_index++;
        else app.media_view.post_index = 0;
    }
    else {
        if (app.media_view.story_index + 1 < app.media_view.story_count) app.media_view.story_index++;
        else app.media_view.story_index = 0;
    }
    loadMedia();
}

hamm.on('swiperight', function (ev) {
    previous();
});

hamm.on('swipeleft', function (ev) {
    next();
});

$("body").keydown(function(ev) {
    switch (ev.which) {
        case 37:
            previous();
            break;
        case 39:
            next();
            break;
    }
});

// HELPER FUNCTIONS ---------------------------------------------------

function getCookie(cname) {
  var name = cname + "=";
  var decodedCookie = decodeURIComponent(document.cookie);
  var ca = decodedCookie.split(';');
  for(var i = 0; i <ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return "";
}

function setCookie(cname, cvalue, exdays) {
  var d = new Date();
  d.setTime(d.getTime() + (exdays*24*60*60*1000));
  var expires = "expires="+ d.toUTCString();
  document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}
