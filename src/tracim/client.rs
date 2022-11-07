use std::time::Duration;

use reqwest::Method;
use serde_json::{json, Map};

use super::{
    account::Account,
    config::Config,
    remote::{Content, CreatedUser, Space, SpaceMember, UserDigest},
    types::{
        AccountId, ContentNamespace, ContentType, Email, Password, RoleInSpace, SessionKey,
        SpaceAccessType, SpaceId, SpaceName,
    },
};

const DEFAULT_CLIENT_TIMEOUT: u64 = 30;

#[derive(Clone)]
pub struct Client {
    config: Config,
}

impl Client {
    pub fn new(config: Config) -> Self {
        Self { config }
    }

    fn client(&self) -> Result<reqwest::blocking::Client, reqwest::Error> {
        Ok(reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(DEFAULT_CLIENT_TIMEOUT))
            .build()?)
    }

    fn authenticated_by_api_key(
        &self,
        method: Method,
        url: String,
    ) -> Result<reqwest::blocking::RequestBuilder, reqwest::Error> {
        Ok(self
            .client()?
            .request(method, url)
            .header("Tracim-Api-Key", &self.config.api_key.0)
            .header("Tracim-Api-Login", &self.config.admin_email.0))
    }

    pub fn get_user_digests(&self) -> Result<Vec<UserDigest>, Error> {
        let url = format!("{}/users", self.config.api_address.0);
        let value = self
            .authenticated_by_api_key(Method::GET, url)?
            .send()?
            .error_for_status()?
            .json()?;
        let user_digests: Vec<UserDigest> = serde_json::from_value(value)?;
        Ok(user_digests)
    }

    pub fn get_spaces(&self) -> Result<Vec<Space>, Error> {
        let url = format!("{}/workspaces", self.config.api_address.0);
        let value = self
            .authenticated_by_api_key(Method::GET, url)?
            .send()?
            .error_for_status()?
            .json()?;
        let spaces: Vec<Space> = serde_json::from_value(value)?;
        Ok(spaces)
    }

    pub fn create_user(self, account: &Account) -> Result<CreatedUser, Error> {
        let url = format!("{}/users", self.config.api_address.0);
        let mut data = Map::new();
        data.insert("email".to_string(), json!(account.email.0));
        data.insert("username".to_string(), json!(account.username.0));
        data.insert("public_name".to_string(), json!(account.username.0));
        data.insert("password".to_string(), json!(account.password.0));
        data.insert("email_notification".to_string(), json!(false));
        data.insert("profile".to_string(), json!("trusted-users"));
        Ok(self
            .authenticated_by_api_key(Method::POST, url)?
            .json(&data)
            .send()?
            .error_for_status()?
            .json::<CreatedUser>()?)
    }

    pub fn update_user_password(
        self,
        account: &Account,
        account_id: AccountId,
        new_password: Password,
    ) -> Result<(), Error> {
        let url = format!(
            "{}/users/{}/password",
            self.config.api_address.0, account_id.0
        );
        let mut data = Map::new();
        data.insert(
            "loggedin_user_password".to_string(),
            json!(account.password.0),
        );
        data.insert("new_password".to_string(), json!(new_password.0));
        data.insert("new_password2".to_string(), json!(new_password.0));
        self.authenticated_by_api_key(Method::PUT, url)?
            .json(&data)
            .send()?
            .error_for_status()?;
        Ok(())
    }

    pub fn update_user_email(
        self,
        account: &Account,
        account_id: AccountId,
        new_email: Email,
    ) -> Result<(), Error> {
        let url = format!("{}/users/{}/email", self.config.api_address.0, account_id.0);
        let mut data = Map::new();
        data.insert(
            "loggedin_user_password".to_string(),
            json!(account.password.0),
        );
        data.insert("email".to_string(), json!(new_email.0));
        self.client()?
            .request(Method::PUT, url)
            .basic_auth(&account.username.0, Some(&account.password.0))
            .json(&data)
            .send()?
            .error_for_status()?;
        Ok(())
    }

    pub fn create_space(
        self,
        name: SpaceName,
        access_type: SpaceAccessType,
        description: String,
    ) -> Result<Space, Error> {
        let url = format!("{}/workspaces", self.config.api_address.0);
        let mut data = Map::new();
        data.insert("access_type".to_string(), json!(access_type.as_str()));
        data.insert("agenda_enabled".to_string(), json!(false));
        data.insert(
            "default_user_role".to_string(),
            json!(RoleInSpace::Reader.as_str()),
        );
        data.insert("description".to_string(), json!(description));
        data.insert("label".to_string(), json!(name.0));
        Ok(self
            .authenticated_by_api_key(Method::POST, url)?
            .json(&data)
            .send()?
            .error_for_status()?
            .json::<Space>()?)
    }

    pub fn space_members(&self, space_id: SpaceId) -> Result<Vec<SpaceMember>, Error> {
        let url = format!(
            "{}/workspaces/{}/members",
            self.config.api_address.0, space_id.0
        );
        let value = self
            .authenticated_by_api_key(Method::GET, url)?
            .send()?
            .error_for_status()?
            .json()?;
        let space_members: Vec<SpaceMember> = serde_json::from_value(value)?;
        Ok(space_members)
    }

    pub fn update_space_member(
        &self,
        space_id: SpaceId,
        account_id: AccountId,
        role: RoleInSpace,
    ) -> Result<(), Error> {
        let url = format!(
            "{}/workspaces/{}/members/{}",
            self.config.api_address.0, space_id.0, account_id.0
        );
        let mut data = Map::new();
        data.insert("role".to_string(), json!(role.as_str()));
        self.authenticated_by_api_key(Method::PUT, url)?
            .json(&data)
            .send()?
            .error_for_status()?;
        Ok(())
    }

    pub fn create_space_member(
        &self,
        space_id: SpaceId,
        account_id: AccountId,
        role: RoleInSpace,
    ) -> Result<(), Error> {
        let url = format!(
            "{}/workspaces/{}/members",
            self.config.api_address.0, space_id.0
        );
        let mut data = Map::new();
        data.insert("role".to_string(), json!(role.as_str()));
        data.insert("user_id".to_string(), json!(account_id.0));
        self.authenticated_by_api_key(Method::POST, url)?
            .json(&data)
            .send()?
            .error_for_status()?;
        Ok(())
    }

    pub fn get_session_key(self, account: &Account) -> Result<SessionKey, Error> {
        let url = format!("{}/auth/login", self.config.api_address.0);
        let mut data = Map::new();
        data.insert("username".to_string(), json!(account.username.0));
        data.insert("password".to_string(), json!(account.password.0));
        let response = self
            .client()?
            .request(Method::POST, url)
            .json(&data)
            .send()?
            .error_for_status()?;
        match response.headers().get("Set-Cookie") {
            Some(header_value) => match header_value.to_str() {
                Ok(value) => {
                    let splitted: Vec<&str> = value.split("session_key=").collect();
                    match splitted.get(1) {
                        Some(value) => {
                            let splitted: Vec<&str> = value.split(";").collect();
                            match splitted.get(0) {
                                Some(session_key) => Ok(SessionKey(session_key.to_string())),
                                None => Err(Error::StructureError(
                                    "Can't read Set-Cookie header value session_key value"
                                        .to_string(),
                                )),
                            }
                        }
                        None => Err(Error::StructureError(
                            "Can't read Set-Cookie header value session_key= part".to_string(),
                        )),
                    }
                }
                Err(_) => Err(Error::StructureError(
                    "Can't read Set-Cookie header value as str".to_string(),
                )),
            },
            None => Err(Error::StructureError(
                "Auth login response don't contains Set-Cookie header".to_string(),
            )),
        }
    }

    pub fn create_publication(
        &self,
        space_id: SpaceId,
        title: &str,
        message: &str,
    ) -> Result<i32, Error> {
        // Create publication content
        let url = format!(
            "{}/workspaces/{}/contents",
            self.config.api_address.0, space_id.0
        );
        let mut data = Map::new();
        data.insert(
            "content_namespace".to_string(),
            json!(ContentNamespace::Publication.as_str()),
        );
        data.insert(
            "content_type".to_string(),
            json!(ContentType::Thread.as_str()),
        );
        data.insert("label".to_string(), json!(title));
        let value = self
            .authenticated_by_api_key(Method::POST, url)?
            .json(&data)
            .send()?
            .error_for_status()?
            .json()?;
        let content: Content = serde_json::from_value(value)?;

        // Create content (first comment)
        let url = format!(
            "{}/workspaces/{}/contents/{}/comments",
            self.config.api_address.0, space_id.0, content.content_id
        );
        let mut data = Map::new();
        data.insert(
            "content_namespace".to_string(),
            json!(ContentNamespace::Publication.as_str()),
        );
        data.insert("raw_content".to_string(), json!(message));
        self.authenticated_by_api_key(Method::POST, url)?
            .json(&data)
            .send()?
            .error_for_status()?;

        Ok(content.content_id)
    }
}

#[derive(Debug)]
pub enum Error {
    UnexpectedError(String),
    StructureError(String),
    NetWorkError(reqwest::Error),
}

impl From<reqwest::Error> for Error {
    fn from(error: reqwest::Error) -> Self {
        if error.is_connect() || error.is_timeout() {
            Self::NetWorkError(error)
        } else {
            Self::UnexpectedError(format!("{}", error))
        }
    }
}

impl From<serde_json::Error> for Error {
    fn from(error: serde_json::Error) -> Self {
        Self::StructureError(format!("{}", error))
    }
}
