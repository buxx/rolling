use std::path::PathBuf;

use pyo3::prelude::*;

use self::error::SpritesheetError;

pub mod error;

#[pyclass]
pub struct CharacterSpriteSheetGenerator {
    builder: lpcg::builder::Builder,
    inspector: lpcg::inspect::Inspector,
}

#[pymethods]
impl CharacterSpriteSheetGenerator {
    #[new]
    pub fn new(spritesheets: String) -> Self {
        Self {
            builder: lpcg::builder::Builder::new(PathBuf::from(&spritesheets)),
            inspector: lpcg::inspect::Inspector::new(PathBuf::from(&spritesheets)),
        }
    }

    pub fn identifiers(&self) -> Vec<String> {
        self.inspector.identifiers()
    }

    pub fn build(
        &self,
        identifiers: &str,
        output: String,
        variant: Option<String>,
    ) -> PyResult<Vec<String>> {
        let input = match lpcg::input::Input::from_str(identifiers, variant) {
            Ok(input) => input,
            Err(error) => {
                return Err(SpritesheetError::new_err(format!(
                    "Can't parse given input : {}",
                    error
                )))
            }
        };
        let build_result = self.builder.build(input);
        let layer_errors = build_result
            .errors
            .iter()
            .map(|error| error.to_string())
            .collect::<Vec<String>>();

        if let Some(output_image) = &build_result.output {
            match output_image.save(&PathBuf::from(output)) {
                Ok(_) => Ok(layer_errors),
                Err(error) => Err(SpritesheetError::new_err(format!(
                    "Failed to save output image : {} (layer errors : '{}')",
                    error,
                    layer_errors.join("', '")
                ))),
            }
        } else {
            Err(SpritesheetError::new_err(format!(
                "No image generated (layer errors : '{}')",
                layer_errors.join("', '")
            )))
        }
    }
}
