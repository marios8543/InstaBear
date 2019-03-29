const params = new URLSearchParams(window.location.search);
const app = new Vue({
  el: "#mainWrap",
  data: {
    current_view: 0, //0:home/search 1:story_view 2:post_view
    total_stories:0,
    total_users: 0,
    total_posts:0,
    st_len: 0,
    posts_len: 0,
    post_idx: 0,
    idx: 0,
    current_story: {
      id: "",
      uploaded: "",
      expires: "",
      media: "",
      ext: "",
      is_video:false,
      user: {
        username: "",
        profile_pic: ""
      }
    },
    forms: {
      username: params.has("username") ? params.get("username") : "",
      account: params.has("account") ? params.get("account") : "",
      d_from: params.has("d_from") ? params.get("d_from") : "",
      d_to: params.has("d_to") ? params.get("d_to") : "",
      poststalk:false,
      notifications:false
    },
    suggestions: [],
    current_post: {
        id: "",
        shortcode: "",
        timestamp: "",
        caption: "",
        ext: "",
        is_video:false
    }
  }
});

var stories = [];
var posts = [];
var store = window.localStorage;

if(params.has("username") || params.has("account") || params.has("d_from") || params.has("d_to")) search();

function search() {
  $.ajax({
    type: "POST",
    url: "search",
    data: {
      'username': app.forms.username,
      'account': app.forms.account,
      'date_from':app.forms.d_from,
      'date_to':app.forms.d_to
    },            
    success: function (data) {
      stories = data;
      app.st_len = data.length;
      loadStory(app.idx = 0);
    },
    dataType: "json"
  }).fail(function (xhr, text, err) { alert(`${text} - ${err}`) });
}

function autoc(val){
  if(val.length>=3){
    $.ajax({
    type: "GET",
    url: "usr_autoc",
    data: {
      'input':val
    },
    success: function (data) {
      app.suggestions = data;
    },
    dataType: "json"
    });
  }
  else app.suggestions = [];
}

function autofield(v){
  app.suggestions = [];
  app.forms.username = v;
}

function loadPosts() {
  $.ajax({
    type: "GET",
    url: "posts",
    data: {
      'username':app.current_story.user.username
    },
    success: function(data) {
      posts = data;
      app.posts_len = data.length;
      loadPost(app.post_idx = 0);
    },
    dataType: "json"
  });
}

function loadPost(i = null) {
  if (i != null){
    app.post_idx = i;
  }
  let pt = posts[app.post_idx];
  app.current_post.id = pt.id;
  app.current_post.shortcode = pt.shortcode;
  app.current_post.ext = pt.ext;
  app.current_post.caption = pt.caption;
  if (pt.ext == "mp4") app.current_post.is_video = true; else app.current_post.is_video = false;
  let uploaded = new Date(parseInt(pt.timestamp) * 1000);
  app.current_post.timestamp = `${uploaded.getDate()}/${uploaded.getMonth()}/${uploaded.getFullYear()} ${uploaded.getHours()}:${uploaded.getMinutes()}`;
  app.current_view = 2;
}

function loadStory(i = null) {
  if (i != null) {
    app.idx = i;
  }
  let st = stories[app.idx];
  app.current_story.id = st.id;
  let uploaded = new Date(parseInt(st.uploaded) * 1000);
  app.current_story.uploaded = `${uploaded.getDate()}/${uploaded.getMonth()}/${uploaded.getFullYear()} ${uploaded.getHours()}:${uploaded.getMinutes()}`;
  app.current_story.ext = st.ext;
  app.current_story.user.username = st.name;
  app.current_story.user.profile_pic = st.current_pfp;
  app.current_story.user.id = st.user_id;
  app.forms.poststalk = parseInt(st.scrape_posts);
  if (st.ext == "mp4") app.current_story.is_video = true; else app.current_story.is_video = false;
  app.current_view = 1;
}

function updatePostStalk() {
  $.ajax({
    type: "GET",
    url: "post_toggle",
    data: {
      'username':app.current_story.user.username
    },
    success: function(data) {
      app.forms.poststalk = parseInt(data);
    },
    dataType: "html"
  }).fail(function(xhr,text,err){ alert(`${JSON.parse(xhr.responseText).message}`); });
}

function previousStory() {
  if (app.idx - 1 >= 0 && app.idx - 1 < stories.length) {
    app.idx--;
  }
  else app.idx = stories.length - 1;
  loadStory();
}

function nextStory() {
  if (app.idx + 1 >= 0 && app.idx + 1 < stories.length) {
    app.idx++;
  }
  else app.idx = 0;
  loadStory();
}

function previousPost() {
  if (app.post_idx - 1 >= 0 && app.post_idx - 1 < posts.length) {
    app.post_idx--;
  }
  else app.post_idx = posts.length - 1;
  loadPost();
}

function nextPost() {
  if (app.post_idx + 1 >= 0 && app.post_idx + 1 < posts.length) {
    app.post_idx++;
  }
  else app.post_idx = 0;
  loadPost();
}

function goBack() {
  if(app.current_view-1>=0){
    app.current_view--;
  }
}

function updateNotif(){
  let feed_list = store.has("notif_list") ? JSON.parse(store.getItem("notif_list")) : false;
  if(feed_list){
    feed_list.push(app.current_story.user.username);
    store.setItem("notif_list",feed_list);
  }
}