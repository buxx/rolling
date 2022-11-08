use serde_derive::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct UserDigest {
    pub user_id: i32,
    pub username: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct CreatedUser {
    pub user_id: i32,
    pub username: String,
    pub email: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Space {
    pub workspace_id: i32,
    pub label: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct SpaceMember {
    pub workspace_id: i32,
    pub user_id: i32,
    pub role: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Content {
    pub workspace_id: i32,
    pub label: String,
    pub content_id: i32,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct MessageSummary {
    pub messages_count: i32,
    pub read_messages_count: i32,
    pub unread_messages_count: i32,
}
