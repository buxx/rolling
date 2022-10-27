use log::info;
use pyo3::prelude::*;

use super::types;

#[pyclass]
pub struct TracimDealer {}

#[pymethods]
impl TracimDealer {
    #[new]
    pub fn new() -> Self {
        Self {}
    }

    pub fn ensure_account(&self, email: String, login: String) -> PyResult<i32> {
        info!("DO STUFF !!");
        println!("PRINTLN");

        PyResult::Ok(types::AccountId(0).0)
    }
}
