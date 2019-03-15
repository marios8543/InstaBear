<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

function nulify($mixed){
  return "";
}

$conn = new mysqli("localhost", "marios", getenv("mysql_password"), "storybear", 3306);
if ($conn->connect_errno) {
    echo "Failed to connect to MySQL: (" . $conn->connect_errno . ") " . $conn->connect_error;
    die;
}
$logged_in = false;
$admin = false;
if($_SERVER['REMOTE_ADDR']==='::1'){
    $logged_in = true;
    $admin = true;
}
else{
    if(isset($_GET['token']) && !empty($_GET['token'])){
        $token = $_GET['token'];
    }
    elseif(isset($_COOKIE['bear_token']) && !empty($_COOKIE['bear_token'])){
      $token = $_COOKIE['bear_token'];
    }
    else die(nulify(http_response_code(403)).'<h1>Δεν δόθηκε κωδικός πρόσβασης</h1>');
    
    $res = $conn->query("SELECT valid,admin FROM tokens WHERE token='".$conn->real_escape_string($token)."';") or die($conn->error);
    $res = $res->fetch_all(MYSQLI_ASSOC);
    if(isset($res[0]['valid']) && $res[0]['valid']){
      setcookie("bear_token",$token,time()+(10*365*24*60*60));
      $logged_in = true;
      $admin = true ? $res[0]['admin']=="1" : false;
      }
      else{
        die(nulify(http_response_code(403)).'<h1>Μη έγκυρος κωδικός πρόσβασης</h1>'); 
    }
}
if(!$logged_in) die(nulify(http_response_code(403))."Not logged in");
$action = null;
if(isset($_GET['action']) && !empty($_GET['action'])) $action = $_GET['action'];

switch($action){
    default:
    $story_count = -1;
    $user_count = -1;
    $post_count = -1;
    $c=0;
    $res = $conn->multi_query("SELECT count(*) FROM stories; SELECT count(*) FROM users; SELECT count(*) FROM posts;");
    do {
      if ($res = $conn->store_result()) {
          $ret = $res->fetch_all(MYSQLI_ASSOC);
          if($c==0) $story_count=$ret[0]['count(*)'];
          elseif($c==1) $user_count=$ret[0]['count(*)'];
          elseif($c==2) $post_count=$ret[0]['count(*)'];
          $res->free();
      }
      $c++;
  } while ($conn->more_results() && $conn->next_result());
    ?>
    <!doctype html>
<html lang="en">

<head>
  <meta charset="utf-8">
  <title>StoryBear</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    html,body {
    width: 100vw;
    height: 100vh;
    overflow-x: hidden;
}

.media-container {
    max-width: 100%;
    max-height: 100%;
    width:100%;
    height: 80%;
}

#storyControls {
    display:inline;
}

.button {
    border-radius: 20%;
    background-color: violet;
    padding: 3px 3px 3px 3px;
}

.profile_pic {
    border-radius: 50%;
}

#metadata {
    text-align: center;
}

.auto-item {
  width: 206px;
  background-color: #d0cbcb;
  border-style: solid;
  border-width: thin;
  border-color: black;
}
.auto-item:hover {
  background-color: #a0a0a0;
}

  </style>
</head>
<body>
  <div id="mainWrap">
    <h1>StoryBear</h1>
    <h4>Bearin' {{ total_stories }} stories and {{ total_posts }} posts from {{ total_users }} users...</h4>
    <hr>
    <div v-if="current_view==0">
      <h3>Search</h3>
      <table style="border-collapse:separate; border-spacing:1em;">
        <tr>
          <td>Username:</td>
          <td>
            <input type="text" v-model="forms.username" placeholder="Username" v-on:input="autoc($event.target.value);">
            <div v-for="itm in suggestions">
              <div class="auto-item" v-on:click="autofield(itm);">{{ itm }}</div>
            </div>
          </td>
        </tr>
        <tr>
          <td>Account:</td>
          <td><input type="text" v-model="forms.account" placeholder="Account"></td>
        </tr>
        <tr>
          <td>Date:
          </td>
          <td>
            From:<input type="date" v-model="forms.d_from" placeholder="From"><br>
            To:&nbsp;&nbsp;<input type="date" v-model="forms.d_to" placeholder="To">
          </td>
        </tr>
        </form>
        <tr>
          <td><button onclick="search();">Search</button></td>
        </tr>
      </table>
    </div>
    <div v-if="current_view==1">
      <button onclick="goBack();">Go Back</button>&nbsp;Found {{ st_len }} stories matching your search.
      <div class="media-container">
        <div v-if="current_story.is_video">
          <video controls loop autoplay class="media-container" v-bind:src="'/storybear.php?action=story_media&id='+current_story.id"></video>
        </div>
        <div v-else>
          <img class="media-container" v-bind:src="'/storybear.php?action=story_media&id='+current_story.id">
        </div>
      </div>
      <br>
      <div id="metadata">
        <div id="storyInfo">
          ID: {{ current_story.id }}<br>
          Uploaded on: {{ current_story.uploaded }}<br>
          User: <a target="_blank" v-bind:href="'https://www.instagram.com/'+current_story.user.username"><img class="profile_pic"
              v-bind:src="current_story.user.profile_pic" width="25" height="25">&nbsp;{{ current_story.user.username }}</a><br>
          <a target="_blank" v-bind:href="'/storybear.php?action=pfps&uid='+current_story.user.id">Profile pictures</a><br>
          <a href="#" onclick="loadPosts();">Posts</a>&nbsp;<input type="checkbox" v-model="forms.poststalk" v-on:change="updatePostStalk()"><br>
        </div>
        <br>
        <nav>
          <button onclick="previousStory();"><</button> {{ idx+1 }}/{{ st_len }} <button onclick="nextStory();">></button>
        </nav>
      </div>
    </div>
    <div v-if="current_view==2">
      <button onclick="goBack();">Go Back</button>&nbsp;Found {{ posts_len }} posts matching your search.
      <div class="media-container">
        <div v-if="current_post.is_video">
          <video controls loop autoplay class="media-container" v-bind:src="'/storybear.php?action=post_media&id='+current_post.id"></video>
        </div>
        <div v-else>
          <img class="media-container" v-bind:src="'/storybear.php?action=post_media&id='+current_post.id">
        </div>
      </div>
      <br>
      <div id="metadata">
        <div id="storyInfo">
          ID: {{ current_post.id }}<br>
          Shortcode: {{ current_post.shortcode }}<br>
          Caption: {{ current_post.caption }}<br>
          Uploaded on: {{ current_post.uploaded }}<br>
          User: <a target="_blank" v-bind:href="'https://www.instagram.com/'+current_story.user.username"><img class="profile_pic"
              v-bind:src="current_story.user.profile_pic" width="25" height="25">&nbsp;{{ current_story.user.username }}</a><br>
          <a target="_blank" v-bind:href="'/storybear.php?action=pfps&uid='+current_story.user.id">Profile pictures</a><br>
        </div>
        <br>
        <nav>
          <button onclick="previousPost();"><</button> {{ post_idx+1 }}/{{ posts_len }} <button onclick="nextPost();">></button>
        </nav>
      </div>
    </div>
  </div>
  <script src="/static/js/jquery-3.3.1.min.js"></script>
  <script src="/static/js/vue.min.js"></script>
  <script>
    const params = new URLSearchParams(window.location.search);
    const app = new Vue({
      el: "#mainWrap",
      data: {
        current_view: 0, //0:home/search 1:story_view 2:post_view
        total_stories: <?=$story_count?>,
        total_users: <?=$user_count?>,
        total_posts:<?=$post_count?>,
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
          poststalk:false
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
    //var autoidx = 0;

    if(params.has("username") || params.has("account") || params.has("d_from") || params.has("d_to")) search();
    

    function search() {
      $.ajax({
        type: "POST",
        url: "storybear.php?action=search",
        data: {
          'username': app.forms.username,
          'account': app.forms.account,
          'date_from':app.forms.d_from,
          'date_to':app.forms.d_to
        },            
        success: function (data) {
          stories = data.stories;
          app.total_stories = data.story_count;
          app.total_users = data.user_count;
          app.st_len = stories.length;
          loadStory(app.idx = 0);
        },
        dataType: "json"
      }).fail(function (xhr, text, err) { alert(`${text} - ${err}`) });
    }

    function autoc(val){
      if(val.length>=2){
        $.ajax({
        type: "GET",
        url: "storybear.php",
        data: {
          'action':'ajax_username',
          'input':val
        },
        success: function (data) {
          app.suggestions = data;
        },
        dataType: "json"
        });
      }
      else app.suggestions = [];
      //autoidx = 0;
    }

    function autofield(v){
      app.suggestions = [];
      app.forms.username = v;
    }

    function loadPosts() {
      $.ajax({
        type: "GET",
        url: "storybear.php",
        data: {
          'action':'fetch_posts',
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
        url: "storybear.php",
        data: {
          'action':'toggle_poststalk',
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

    function toggle_posts(id){
      
    }

    $(document).keypress(function (e) {
      if (app.current_view == 0){
        if (e.which == 13) search();
        /*
        if (e.which == 40) autodown();
        if (e.which == 38) autoup();
        */
      }
      if (app.current_view == 1) {
        if (e.which == 37) previousStory();
        else if (e.which == 39) nextStory();
      }
    });
  </script>
</body>

</html>
<?php
    case 'search':
    $username = false;
    $date_from = false;
    $date_to = false;
    $account = false;
    if(isset($_POST['username']) && !empty($_POST['username'])){
        $username = $_POST['username'];
    }
    if(isset($_POST['account']) && !empty($_POST['account'])){
            $account = $_POST['account'];
    }
    if(isset($_POST['from_date']) && !empty($_POST['from_date'])){
            $date_from = strptime($_POST['from_date'],"MM/DD/YYYY");
    }
    if(isset($_POST['to_date']) && !empty($_POST['to_date'])){
        $date_to = strptime($_POST['to_date'],"MM/DD/YYYY");
    }
    if(!$username && !$date_from && !$date_to && !$account) die;
    $sql="SELECT count(*) FROM stories; SELECT count(*) FROM users; SELECT stories.uploaded,stories.id,users.name,users.current_pfp,stories.ext,stories.user_id,users.scrape_posts FROM stories INNER JOIN users ON stories.user_id = users.id WHERE ";
    $count=0;
    if($username!=false){
        $sql .= "user_id=(SELECT id FROM users WHERE name LIKE '%".$conn->real_escape_string($username)."%')";
        $count++;
    }
    if($account!=false){
        $subsql="account='".$conn->real_escape_string($account)."'";
        if($count>0){
            $sql.=" AND ".$subsql;
        }
        else {
            $sql.=$subsql;
        }
        $count++;
    }
    if($date_from!=false && $date_to!=false){
        $subsql="uploaded >= ".$conn->real_escape_string($date_from)." AND uploaded <=".$conn->real_escape_string($date_to);
        if($count>0){
            $sql.=" AND ".$subsql;
        }
        else {
            $sql.=$subsql;
        }
        $count++;
    }
    if(!$conn->multi_query($sql)){
        http_response_code(500);
        die(json_encode(["message"=>$conn->error]));
    }
    $return = ["story_count"=>"","user_count"=>"","stories"=>[]];
    $c=0;
    do {
        if ($res = $conn->store_result()) {
            $ret = $res->fetch_all(MYSQLI_ASSOC);
            if($c==0) $return["story_count"]=$ret[0]['count(*)'];
            elseif($c==1) $return["user_count"]=$ret[0]['count(*)'];
            else $return["stories"]=$ret;
            $res->free();
        }
        $c++;
    } while ($conn->more_results() && $conn->next_result());
    header("Content-Type: application/json");
    if(sizeof($return["stories"])==0) http_response_code(404){
        $return['message'] = "No stories found"
    };
    echo json_encode($return);
    break;

    case 'story_media':
    if(isset($_GET['id']) && !empty($_GET['id'])){
        $sql = "SELECT media,ext FROM stories WHERE id=".$conn->real_escape_string($_GET['id']);
        $res = $conn->query($sql) or die(http_response_code(404));
        $res = $res->fetch_assoc();
        if($res['ext']=="jpg") header("Content-Type: image/jpeg");
        elseif($res['ext']=="mp4") header("Content-Type: video/mp4");
        else header("Content-Type: application/octet-stream");
        header("Content-Disposition: inline; ");
        header("Content-Length: ".strlen($res['media']));
        echo $res['media'];
        http_response_code(200);
    }
    else http_response_code(400);
    break;
    
    case 'tokens':
    if($admin){
      $res = $conn->query("SELECT * FROM tokens");
      $res = $res->fetch_all(MYSQLI_ASSOC);
      //echo '<pre>' , var_dump($res) , '</pre>';
      ?>
      <!doctype html>
      <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>StoryBear Tokens</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        table, th, td {
          border: 1px solid black;
        }
        td {
          text-align: center;
        }
      </style>
      </head>
      <body>
        <h1>Storybear Access Tokens</h1><br><br>
        <table>
          <tr>
            <th>Token</th>
            <th>Created on</th> 
            <th>Valid</th>
            <th>Admin</th>
            <th>Validate/
              Invalidate</th>
            <th>Add/Remove
              Admin</th>
          </tr>
          <?php for($i=0;$i<count($res);$i++) { $data = $res[$i];?>
          <tr>
            <td><?=$data['token']?></td>
            <td><?=$data['created']?></td>
            <td><?=var_export((bool)$data['valid'], true);?></td>
            <td><?=var_export((bool)$data['admin'], true);?></td>
            <td><a href="storybear.php?action=invalidate_token&tkn=<?=$data['token']?>">🗑️</a></td>
            <td><a href="storybear.php?action=make_admin&tkn=<?=$data['token']?>">👮</a></td>       
          </tr>
          <?php } ?>
        </table>
        <br><br>
        <h3>Create token</h3>
        <form action="storybear.php?action=create_token" method="POST">
          Token: <input id="tknInput" type="text" name="tkn">&nbsp;<button type="button" onclick="random();">Random</button><br><br>
          Admin: <input type="checkbox" name="admin" value="1"><br><br>
          <input type="submit">
        </form>
        <script>
        function random(){
          const max = 1000000000;
          const min = 0;
          document.getElementById("tknInput").value = Math.round(Math.random() * (max-min) + min );
        }
        </script>
      </body>
      </html> <?php
    }
    else die("δεν εχετε δικαιωματα διαχειριστη ".nulify(http_response_code(403)));
    break;
    
    case 'create_token':
    if($admin){
        if(isset($_POST['tkn']) && !empty($_POST['tkn'])){
            if(isset($_POST['admin']) && $_POST['admin']=="1") $admn = true;
            $tkn = $conn->real_escape_string($_POST['tkn']);
            $res = $conn->query("INSERT INTO tokens(token,admin) values('$tkn','$admn')");
            if($res) header("Location: /storybear.php?action=tokens");
            else die($conn->error);
        }
    }
    else die("δεν εχετε δικαιωματα διαχειριστη ".nulify(http_response_code(403)));
    break;

    case 'make_admin':
    if($admin){
        if(isset($_GET['tkn']) && !empty($_GET['tkn'])){
            $tkn = $conn->real_escape_string($_GET['tkn']);
            $res = $conn->query("
            CASE WHEN ( (SELECT admin FROM tokens WHERE token='$tkn') = 1 )
                THEN UPDATE tokens SET admin=0 WHERE token='$tkn';
                ELSE UPDATE tokens SET admin=1 WHERE token='$tkn';
            END CASE
            ");
            if($res) header("Location: /storybear.php?action=tokens");
            else die($conn->error);
        }
    }
    else die("δεν εχετε δικαιωματα διαχειριστη ".nulify(http_response_code(403)));
    break;

    case 'invalidate_token':
    if($admin){
        if(isset($_GET['tkn']) && !empty($_GET['tkn'])){
            $tkn = $conn->real_escape_string($_GET['tkn']);
            $res = $conn->query("
            CASE WHEN ( (SELECT valid FROM tokens WHERE token='$tkn') = 1 )
                THEN UPDATE tokens SET valid=0 WHERE token='$tkn';
                ELSE UPDATE tokens SET valid=1 WHERE token='$tkn';
            END CASE
            ");
            if($res) header("Location: /storybear.php?action=tokens");
            else die($conn->error);
        }
    }
    else die("δεν εχετε δικαιωματα διαχειριστη ".nulify(http_response_code(403)));
    break;

    case 'pfps':
    if(isset($_GET['uid']) && !empty($_GET['uid'])){
        $uid = $_GET['uid'];
        $res = $conn->query("SELECT media,timestamp FROM profile_pictures WHERE user_id=".$conn->real_escape_string($uid));
        $res = $res->fetch_all(MYSQLI_ASSOC);
        for($i=0;$i<count($res);$i++){
            $img = base64_encode($res[$i]['media']);
            ?><img src="data:image/jpeg;base64, <?=$img?>">&nbsp;<?=$res[$i]['timestamp']?><br><br>
        <?php }
    }
    break;

    case 'ajax_username':
    if(isset($_GET['input']) && !empty($_GET['input'])){
        $input = $conn->real_escape_string($_GET['input']);
        header("Content-Type: application/json");
        $res = $conn->query("SELECT name FROM users WHERE name LIKE '%$input%'");
        if(!$res) die('[]');
        $res = $res->fetch_all(MYSQLI_ASSOC);
        $ret = [];
        for($i=0;$i<count($res);$i++){
            array_push($ret,$res[$i]['name']);
        }
        echo json_encode($ret);
    }
    break;

    case 'fetch_posts':
    if(isset($_GET['username']) && !empty($_GET['username'])){
      $username = $conn->real_escape_string($_GET['username']);
      header("Content-Type: application/json");
      $res = $conn->query("SELECT id,shortcode,caption,ext,timestamp FROM posts WHERE user_id=(SELECT id FROM users WHERE name='$username')");
      if(!$res) die('[]');
      $res = $res->fetch_all(MYSQLI_ASSOC);
      echo json_encode($res);
    }
    break;

    case 'post_media':
    if(isset($_GET['id']) && !empty($_GET['id'])){
        $sql = "SELECT media,ext FROM posts WHERE id=".$conn->real_escape_string($_GET['id']);
        $res = $conn->query($sql) or die(http_response_code(404));
        $res = $res->fetch_assoc();
        if($res['ext']=="jpg") header("Content-Type: image/jpeg");
        elseif($res['ext']=="mp4") header("Content-Type: video/mp4");
        else header("Content-Type: application/octet-stream");
        header("Content-Disposition: inline; ");
        header("Content-Length: ".strlen($res['media']));
        echo $res['media'];
        http_response_code(200);
    }
    else http_response_code(400);
    break;

    case 'toggle_poststalk':
    if(!$admin) die(json_encode(array('message'=>'μονο οι διαχειριστες μπορουν να το κανουν αυτο')).nulify(header("Content-Type: application/json").http_response_code(403)));
    if(isset($_GET['username']) && !empty($_GET['username'])){
      $username = $conn->real_escape_string($_GET['username']);
      $sql = "
      CASE WHEN ( (SELECT scrape_posts FROM users WHERE name='$username') = 1 )
        THEN UPDATE users SET scrape_posts=0 WHERE name='$username';
        SELECT 0;
        ELSE UPDATE users SET scrape_posts=1 WHERE name='$username';
        SELECT 1;
      END CASE
      ";
      $res = $conn->query($sql);
      $res = $res->fetch_array(MYSQLI_NUM);
      echo $res[0];
    }
}
?>