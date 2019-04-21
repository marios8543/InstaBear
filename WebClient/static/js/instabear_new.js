// VIEW RENDERING ---------------------------------------------------------------------------

const app = new Vue({
    el: "#mainWrap",
    data: {
        methods:{
            register_autoc:function(itm){
                app.inputs.username = itm;
                app.inputs.suggestions = [];
            },
            formatTimestamp:function(timestamp) {
                let ts = new Date(timestamp * 1000);
                return `${ts.getDate()}/${ts.getMonth()}/${ts.getFullYear()} ${ts.getHours()}:${ts.getMinutes()}`;
            }
        },
        current_view: "home",
        story_count: 0,
        post_count: 0,
        user_count: 0,
        inputs: {
            username: "",
            account: "",
            suggestions: []
        },
        latest_story: {
            user: {
                name: "",
                profile_pic: ""
            },
            id: "",
            timestamp: ""
        },
        postwatch: [],
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
        }
    }
});


var stories = [];
var posts = [];

app.methods.autoc = function autoc(val) {
    if (val.length >= 3) {
        $.ajax({
            type: "GET",
            url: "usr_autoc",
            data: {
                'input': val
            },
            success: function (data) {
                app.inputs.suggestions = data;
            },
            dataType: "json"
        });
    }
    else app.inputs.suggestions = [];
}

app.methods.search = function search() {
    $.ajax({

        type: "POST",
        url: "search",
        data: {
            'username': app.inputs.username,
            'account': app.inputs.account,
        },
        success: function (data) {
            stories = data;
            app.media_view.story_count = data.length;
            app.media_view.story_index = 0;
            loadMedia();
        },
        dataType: "json"
    }).fail(function (xhr, text, err) { alert(`${text} - ${err}`) });
}

app.methods.toggleView = function toggleView() {
    if (app.media_view.post) {
        app.media_view.post = false;
    }
    else {
        if (posts.length == 0) {
            fetchPosts();
            if (posts.length == 0) {
                return;
            }
            else {
                app.media_view.post = true;
            }
        }
        else {
            app.media_view.post = true;
        }
    }
    loadMedia();
}

app.methods.togglePosts = function togglePosts() {
    $.ajax({
        type: "GET",
        url: "post_toggle",
        data: {
            'username': app.media_view.user.name
        },
        success: function (data) {
            app.forms.poststalk = parseInt(data);
        },
        dataType: "html"
    }).fail(function (xhr, text, err) { alert(`${JSON.parse(xhr.responseText).message}`); });
}

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
hamm.get('swipe').set({ direction: Hammer.DIRECTION_ALL });

hamm.on('swiperight', function (ev) {
    //PREVIOUS
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
});

hamm.on('swipeleft', function (ev) {
    //NEXT
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

});

/*hamm.on('swipeup', function (ev) {
    if(app.current_view=='media_view') app.show_meta = true;
});*/