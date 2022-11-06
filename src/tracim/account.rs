use pyo3::prelude::*;

use super::types::{Email, Password, Username};

#[pyclass]
#[derive(Clone)]
pub struct Account {
    pub username: Username,
    pub password: Password,
    pub email: Email,
}

#[pymethods]
impl Account {
    #[new]
    pub fn new(username: Username, password: Password, email: Email) -> Self {
        Self {
            username,
            password,
            email,
        }
    }
}
