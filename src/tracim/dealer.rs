use pyo3::prelude::*;

use crate::tracim::types::{AccountId, Email, Password, RoleInSpace, SpaceName};

use super::{account::Account, client::Client, config::Config, error::TracimError, types::SpaceId};

#[pyclass]
pub struct Dealer {
    config: Config,
}

#[pymethods]
impl Dealer {
    #[new]
    pub fn new(config: Config) -> Self {
        Self { config }
    }

    pub fn ensure_account(&self, account: Account) -> PyResult<i32> {
        let user_digests = Client::new(self.config.clone()).get_user_digests()?;
        for user_digest in &user_digests {
            if user_digest.username == account.username.0 {
                return PyResult::Ok(user_digest.user_id);
            }
        }

        PyResult::Ok(
            Client::new(self.config.clone())
                .create_user(&account)?
                .user_id,
        )
    }

    pub fn create_account(&self, account: Account) -> PyResult<i32> {
        PyResult::Ok(
            Client::new(self.config.clone())
                .create_user(&account)?
                .user_id,
        )
    }

    pub fn set_account_password(
        &self,
        account: Account,
        account_id: AccountId,
        new_password: Password,
    ) -> PyResult<()> {
        Client::new(self.config.clone()).update_user_password(
            &account,
            account_id,
            new_password,
        )?;
        Ok(())
    }

    pub fn set_account_email(
        &self,
        account: Account,
        account_id: AccountId,
        new_email: Email,
    ) -> PyResult<()> {
        Client::new(self.config.clone()).update_user_email(&account, account_id, new_email)?;
        Ok(())
    }

    pub fn get_new_session_key(&self, account: Account) -> PyResult<String> {
        PyResult::Ok(
            Client::new(self.config.clone())
                .get_session_key(&account)?
                .0,
        )
    }

    pub fn ensure_space(&self, name: SpaceName) -> PyResult<i32> {
        let spaces = Client::new(self.config.clone()).get_spaces()?;

        for space in &spaces {
            if space.label == name.0 {
                return PyResult::Ok(space.workspace_id);
            }
        }

        PyResult::Ok(
            Client::new(self.config.clone())
                .create_space(
                    name,
                    super::types::SpaceAccessType::Confidential,
                    "".to_string(),
                )?
                .workspace_id,
        )
    }

    pub fn ensure_space_role(
        &self,
        space_id: SpaceId,
        account_id: AccountId,
        // TODO : role as enum
        role: &str,
    ) -> PyResult<()> {
        let role_ = match RoleInSpace::from_str(&role) {
            Some(role_) => role_,
            None => return Err(TracimError::new_err(format!("Unknown role '{}'", role))),
        };
        let space_members = Client::new(self.config.clone()).space_members(space_id.clone())?;

        for space_member in &space_members {
            if space_member.user_id == account_id.0 {
                if space_member.role == role_.as_str() {
                    return Ok(());
                } else {
                    Client::new(self.config.clone()).update_space_member(
                        space_id.clone(),
                        account_id,
                        role_,
                    )?;
                    return Ok(());
                }
            }
        }

        Client::new(self.config.clone()).create_space_member(
            space_id.clone(),
            account_id,
            role_,
        )?;

        Ok(())
    }

    pub fn ensure_not_in_space(&self, space_id: SpaceId, account_id: AccountId) -> PyResult<()> {
        let space_members = Client::new(self.config.clone()).space_members(space_id.clone())?;

        for space_member in &space_members {
            if &space_member.user_id == &account_id.0 {
                Client::new(self.config.clone())
                    .remove_space_member(space_id.clone(), account_id.clone())?;
            }
        }

        Ok(())
    }

    pub fn create_publication(
        &self,
        space_id: SpaceId,
        title: &str,
        message: &str,
    ) -> PyResult<()> {
        Client::new(self.config.clone()).create_publication(space_id.clone(), title, message)?;
        return Ok(());
    }

    pub fn get_unread_messages_count(
        &self,
        account: Account,
        account_id: AccountId,
    ) -> PyResult<i32> {
        return Ok(Client::new(self.config.clone())
            .get_message_summary(&account, account_id.clone(), Some(account_id.clone()), Some("user_call.created,user.*,workspace.modified,workspace.deleted,workspace.undeleted,workspace_member.modified,workspace_member.deleted,content.modified,reaction.*,tag.*,content_tag.*".to_string(),))?
            .unread_messages_count);
    }

    pub fn space_slug_used(&self, slug: String) -> PyResult<bool> {
        let spaces = Client::new(self.config.clone()).get_spaces()?;

        for space in &spaces {
            if space.slug == slug {
                return PyResult::Ok(true);
            }
        }

        PyResult::Ok(false)
    }
}
