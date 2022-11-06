use pyo3::prelude::*;
use tracim::{
    account::Account,
    config::Config,
    dealer::Dealer,
    error::{AccountNotFoundError, TracimError},
    types::{
        AccountId, ApiAddress, ApiKey, Email, Password, SessionKey, SpaceId, SpaceName, Username,
    },
};

pub mod tracim;

#[pymodule]
fn rrolling(py: Python, m: &PyModule) -> PyResult<()> {
    // TODO: Move these in tracim module
    m.add("TracimError", py.get_type::<TracimError>())?;
    m.add(
        "AccountNotFoundError",
        py.get_type::<AccountNotFoundError>(),
    )?;
    m.add_class::<Config>()?;
    m.add_class::<Dealer>()?;
    m.add_class::<Account>()?;
    m.add_class::<Username>()?;
    m.add_class::<Password>()?;
    m.add_class::<Email>()?;
    m.add_class::<ApiKey>()?;
    m.add_class::<ApiAddress>()?;
    m.add_class::<SessionKey>()?;
    m.add_class::<AccountId>()?;
    m.add_class::<SpaceId>()?;
    m.add_class::<SpaceName>()?;

    Ok(())
}
