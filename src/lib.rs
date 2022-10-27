use pyo3::prelude::*;

pub mod tracim;

#[pymodule]
fn rrolling(_py: Python, m: &PyModule) -> PyResult<()> {
    pyo3_log::init();

    m.add_class::<tracim::dealer::TracimDealer>()?;
    Ok(())
}
