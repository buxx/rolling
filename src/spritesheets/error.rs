use pyo3::create_exception;

create_exception!(error, SpritesheetError, pyo3::exceptions::PyException);
