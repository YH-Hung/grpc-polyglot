use std::{io, path::PathBuf};
use thiserror::Error;

/// Custom error type for protoc-http-rs
#[derive(Error, Debug)]
#[allow(dead_code)] // Some variants are defined for future use
pub enum Error {
    #[error("IO error: {0}")]
    Io(#[from] io::Error),

    #[error("Parse error in file {file:?}: {message}")]
    Parse { file: PathBuf, message: String },

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Code generation error: {0}")]
    CodeGen(String),

    #[error("Invalid proto type: {proto_type}")]
    InvalidProtoType { proto_type: String },

    #[error("Missing required field: {field}")]
    MissingField { field: String },

    #[error("Invalid identifier: {identifier}")]
    InvalidIdentifier { identifier: String },

    #[error("JSON error: {0}")]
    Json(String),
}

/// Result type alias for protoc-http-rs
pub type Result<T> = std::result::Result<T, Error>;

impl From<serde_json::Error> for Error {
    fn from(err: serde_json::Error) -> Self {
        Error::Json(err.to_string())
    }
}

impl Error {
    pub fn parse_error(file: impl Into<PathBuf>, message: impl Into<String>) -> Self {
        Self::Parse {
            file: file.into(),
            message: message.into(),
        }
    }

    pub fn validation_error(message: impl Into<String>) -> Self {
        Self::Validation(message.into())
    }

    pub fn codegen_error(message: impl Into<String>) -> Self {
        Self::CodeGen(message.into())
    }
}
