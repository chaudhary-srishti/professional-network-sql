# Professional Network — Relational ERD

```mermaid
erDiagram
    users ||--o{ organization_members : "is member"
    organizations ||--o{ organization_members : "has member"

    users ||--o{ user_connections : "requester"
    users ||--o{ user_connections : "target"
    users ||--o{ organization_follows : "follows"
    organizations ||--o{ organization_follows : "followed by"
    users ||--o{ firm_member_requests : "applicant"
    organizations ||--o{ firm_member_requests : "requested"

    users ||--o{ posts : "authors"
    organizations ||--o{ posts : "posted as"
    users ||--o{ articles : "authors"
    organizations ||--o{ articles : "posted as"
    posts ||--o{ posts : "shared_post"
    articles ||--o{ posts : "shared_article"

    users ||--o{ comments : "authors"
    posts ||--o{ comments : "on post"
    articles ||--o{ comments : "on article"

    users ||--o{ likes : "by user"
    posts ||--o{ likes : "on post"
    articles ||--o{ likes : "on article"
    comments ||--o{ likes : "on comment (reply_like)"

    users {
        uuid id PK
        citext email UK
        text name
        text current_title
        text current_company
        bool super_admin
        timestamptz created_at
        timestamptz updated_at
        timestamptz last_login
    }
    organizations {
        uuid id PK
        text firm_url UK
        text name
        text[] categories
        timestamptz created_at
        timestamptz updated_at
    }
    organization_members {
        uuid organization_id PK,FK
        uuid user_id PK,FK
        text role
        timestamptz added_at
    }
    user_connections {
        uuid id PK
        uuid requester_id FK
        uuid target_id FK
        link_status status
        text personal_note
    }
    organization_follows {
        uuid id PK
        uuid user_id FK
        uuid organization_id FK
    }
    firm_member_requests {
        uuid id PK
        uuid user_id FK
        uuid organization_id FK
        link_status status
    }
    posts {
        uuid id PK
        uuid author_id FK
        uuid firm_id FK
        text[] hashtags
        uuid shared_post_id FK
        uuid shared_article_id FK
        int like_count
        int comment_count
    }
    articles {
        uuid id PK
        uuid author_id FK
        uuid firm_id FK
        text cover_image
        int like_count
        int comment_count
    }
    comments {
        uuid id PK
        uuid author_id FK
        uuid post_id FK
        uuid article_id FK
        text body
        int like_count
    }
    likes {
        uuid id PK
        uuid user_id FK
        uuid post_id FK
        uuid article_id FK
        uuid comment_id FK
    }
```

Notes:
- `posts`/`articles` → `organizations` (`firm_id`) is optional (`ON DELETE SET NULL`).
- `comments` targets exactly one of `post_id`/`article_id`; `likes` exactly one of
  `post_id`/`article_id`/`comment_id` (CHECK constraints).
- `likes.comment_id` is the self-referential Mongo `reply_like`.
