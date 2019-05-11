FETCH_STORY_REEL = "https://www.instagram.com/graphql/query/?query_hash=60b755363b5c230111347a7a4e242001&variables={%22only_stories%22:true}"

FETCH_STORIES = 'https://www.instagram.com/graphql/query/?query_hash=eb1918431e946dd39bf8cf8fb870e426&variables={{"reel_ids":{},"tag_names":[],"location_ids":[],"highlight_reel_ids":[],"precomposed_overlay":false,"show_story_viewer_list":true,"story_viewer_fetch_count":50,"story_viewer_cursor":""}}'

LOGIN = 'https://www.instagram.com/accounts/login/ajax/'

HOME = 'https://www.instagram.com/'

POSTS = 'https://www.instagram.com/graphql/query/?query_hash=f2405b236d85e8296cf30347c9f08c2a&variables={}'

sql_queries = [
  """
CREATE TABLE IF NOT EXISTS `posts` (
  `id` bigint(255) DEFAULT NULL,
  `user_id` bigint(255) DEFAULT NULL,
  `shortcode` varchar(255) DEFAULT NULL,
  `caption` text,
  `media` longblob,
  `ext` varchar(255) NOT NULL,
  `timestamp` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""",
  """
CREATE TABLE IF NOT EXISTS `profile_pictures` (
  `id` varchar(255) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `media` blob,
  `timestamp` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""",
  """
CREATE TABLE IF NOT EXISTS `stories` (
  `id` bigint(20) DEFAULT NULL,
  `uploaded` bigint(255) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `media` longblob,
  `ext` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""",
  """
CREATE TABLE IF NOT EXISTS `tokens` (
  `token` varchar(255) DEFAULT NULL,
  `valid` tinyint(4) DEFAULT '1',
  `admin` tinyint(4) NOT NULL DEFAULT '0',
  `created` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `id` bigint(20) DEFAULT NULL,
  `session_id` varchar(255) DEFAULT NULL,
  `interval` int(11) NOT NULL DEFAULT '15'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""",
  """
CREATE TABLE IF NOT EXISTS `users` (
  `id` bigint(20) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `account` varchar(255) DEFAULT NULL,
  `current_pfp` varchar(255) DEFAULT NULL,
  `scrape_posts` tinyint(4) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""",
  """ALTER TABLE `posts`
  ADD KEY `id` (`id`);
  """,
  """
  ALTER TABLE `stories`
  ADD KEY `id` (`id`);
  """,
  """
  ALTER TABLE `users`
  ADD UNIQUE KEY `id` (`id`);
  """
]
