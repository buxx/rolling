use pyo3::prelude::*;
use spritesheets::{error::SpritesheetError, CharacterSpriteSheetGenerator};
use tracim::{
    account::Account,
    config::Config,
    dealer::Dealer,
    error::{AccountNotFoundError, TracimError},
    types::{
        AccountId, ApiAddress, ApiKey, Email, Password, SessionKey, SpaceId, SpaceName, Username,
    },
};

pub mod spritesheets;
pub mod tracim;

#[pymodule]
fn rrolling(py: Python, root_module: &PyModule) -> PyResult<()> {
    let tracim_module = PyModule::new(py, "tracim")?;
    let spritesheets_module = PyModule::new(py, "spritesheets")?;

    tracim_module.add("TracimError", py.get_type::<TracimError>())?;
    tracim_module.add(
        "AccountNotFoundError",
        py.get_type::<AccountNotFoundError>(),
    )?;
    tracim_module.add_class::<Config>()?;
    tracim_module.add_class::<Dealer>()?;
    tracim_module.add_class::<Account>()?;
    tracim_module.add_class::<Username>()?;
    tracim_module.add_class::<Password>()?;
    tracim_module.add_class::<Email>()?;
    tracim_module.add_class::<ApiKey>()?;
    tracim_module.add_class::<ApiAddress>()?;
    tracim_module.add_class::<SessionKey>()?;
    tracim_module.add_class::<AccountId>()?;
    tracim_module.add_class::<SpaceId>()?;
    tracim_module.add_class::<SpaceName>()?;

    spritesheets_module.add("SpritesheetError", py.get_type::<SpritesheetError>())?;
    spritesheets_module.add_class::<CharacterSpriteSheetGenerator>()?;

    root_module.add_submodule(tracim_module)?;
    root_module.add_submodule(spritesheets_module)?;

    Ok(())
}
