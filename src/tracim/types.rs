use pyo3::prelude::*;

#[pyclass]
#[derive(Clone)]
pub struct AccountId(pub i32);

#[pymethods]
impl AccountId {
    #[new]
    pub fn new(id: i32) -> Self {
        Self(id)
    }
}

#[pyclass]
#[derive(Clone)]
pub struct SpaceId(pub i32);

#[pymethods]
impl SpaceId {
    #[new]
    pub fn new(id: i32) -> Self {
        Self(id)
    }
}

#[pyclass]
#[derive(Clone, PartialEq)]
pub struct SpaceName(pub String);

#[pymethods]
impl SpaceName {
    #[new]
    pub fn new(name: String) -> Self {
        Self(name)
    }
}

#[pyclass]
#[derive(Clone, PartialEq)]
pub struct Email(pub String);

#[pymethods]
impl Email {
    #[new]
    pub fn new(email: String) -> Self {
        Self(email)
    }
}

#[pyclass]
#[derive(Clone, PartialEq)]
pub struct Username(pub String);

#[pymethods]
impl Username {
    #[new]
    pub fn new(username: String) -> Self {
        Self(username)
    }
}

#[pyclass]
#[derive(Clone, PartialEq)]
pub struct Password(pub String);

#[pymethods]
impl Password {
    #[new]
    pub fn new(password: String) -> Self {
        Self(password)
    }
}

#[pyclass]
#[derive(Clone, PartialEq)]
pub struct ApiKey(pub String);

#[pymethods]
impl ApiKey {
    #[new]
    pub fn new(key: String) -> Self {
        Self(key)
    }
}

#[pyclass]
#[derive(Clone, PartialEq)]
pub struct ApiAddress(pub String);

#[pymethods]
impl ApiAddress {
    #[new]
    pub fn new(address: String) -> Self {
        Self(address)
    }
}

#[pyclass]
#[derive(Clone, PartialEq)]
pub struct SessionKey(pub String);

#[pymethods]
impl SessionKey {
    #[new]
    pub fn new(key: String) -> Self {
        Self(key)
    }
}

pub enum RoleInSpace {
    Reader,
    Contributor,
    ContentManager,
    WorkspaceManager,
}

impl RoleInSpace {
    pub fn from_str(value: &str) -> Option<Self> {
        match value {
            "reader" => Some(Self::Reader),
            "contributor" => Some(Self::Contributor),
            "content-manager" => Some(Self::ContentManager),
            "workspace-manager" => Some(Self::WorkspaceManager),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &str {
        match self {
            Self::Reader => "reader",
            Self::Contributor => "contributor",
            Self::ContentManager => "content-manager",
            Self::WorkspaceManager => "workspace-manager",
        }
    }
}

pub enum SpaceAccessType {
    Confidential,
    OnRequest,
    Open,
}

impl SpaceAccessType {
    pub fn from_str(value: &str) -> Option<Self> {
        match value {
            "confidential" => Some(Self::Confidential),
            "on_request" => Some(Self::OnRequest),
            "open" => Some(Self::Open),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &str {
        match self {
            Self::Confidential => "confidential",
            Self::OnRequest => "on_request",
            Self::Open => "open",
        }
    }
}

pub enum ContentType {
    Thread,
    File,
    Note,
    Folder,
    Kanban,
    Todo,
    Comment,
}

impl ContentType {
    pub fn from_str(value: &str) -> Option<Self> {
        match value {
            "thread" => Some(Self::Thread),
            "file" => Some(Self::File),
            "html-document" => Some(Self::Note),
            "folder" => Some(Self::Folder),
            "kanban" => Some(Self::Kanban),
            "todo" => Some(Self::Todo),
            "comment" => Some(Self::Comment),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &str {
        match self {
            Self::Thread => "thread",
            Self::File => "file",
            Self::Note => "html-document",
            Self::Folder => "folder",
            Self::Kanban => "kanban",
            Self::Todo => "todo",
            Self::Comment => "comment",
        }
    }
}

pub enum ContentNamespace {
    Content,
    Publication,
}

impl ContentNamespace {
    pub fn from_str(value: &str) -> Option<Self> {
        match value {
            "content" => Some(Self::Content),
            "publication" => Some(Self::Publication),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &str {
        match self {
            Self::Content => "content",
            Self::Publication => "publication",
        }
    }
}
