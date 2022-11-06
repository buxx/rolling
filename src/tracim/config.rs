use pyo3::prelude::*;

use super::types::{ApiAddress, ApiKey, Email};

#[pyclass]
#[derive(Clone)]
pub struct Config {
    pub api_key: ApiKey,
    pub api_address: ApiAddress,
    pub admin_email: Email,
}

#[pymethods]
impl Config {
    #[new]
    pub fn new(api_key: ApiKey, api_address: ApiAddress, admin_email: Email) -> Self {
        let api_address = ApiAddress(api_address.0.trim_end_matches("/").to_string());
        Self {
            api_key,
            api_address,
            admin_email,
        }
    }
}
