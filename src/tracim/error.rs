use pyo3::{create_exception, PyErr};

use super::client::Error as ClientError;

create_exception!(error, TracimError, pyo3::exceptions::PyException);
create_exception!(error, AccountNotFoundError, pyo3::exceptions::PyException);

impl From<ClientError> for PyErr {
    fn from(error: ClientError) -> Self {
        match error {
            ClientError::NetWorkError(error) => {
                TracimError::new_err(format!("Network error : {}", error))
            }
            ClientError::UnexpectedError(error) => {
                TracimError::new_err(format!("Unexpected error : {error}"))
            }
            ClientError::StructureError(error) => {
                TracimError::new_err(format!("Structure error : {error}"))
            }
        }
    }
}
