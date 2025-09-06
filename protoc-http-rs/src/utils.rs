use crate::error::Result;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

/// Find all .proto files in a directory recursively
pub fn find_proto_files(root: &Path) -> Result<Vec<PathBuf>> {
    let mut files = WalkDir::new(root)
        .into_iter()
        .filter_map(|entry| entry.ok())
        .filter(|entry| {
            entry
                .path()
                .extension()
                .and_then(|s| s.to_str())
                .map_or(false, |ext| ext == "proto")
        })
        .map(|entry| entry.path().to_path_buf())
        .collect::<Vec<_>>();

    files.sort();
    Ok(files)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::io::Write;
    use tempfile::TempDir;

    #[test]
    fn test_find_proto_files() {
        let temp_dir = TempDir::new().unwrap();
        let proto_dir = temp_dir.path().join("protos");
        fs::create_dir_all(&proto_dir).unwrap();

        // Create test proto files
        let mut file1 = fs::File::create(proto_dir.join("test1.proto")).unwrap();
        writeln!(file1, "syntax = \"proto3\";").unwrap();

        let mut file2 = fs::File::create(proto_dir.join("test2.proto")).unwrap();
        writeln!(file2, "syntax = \"proto3\";").unwrap();

        // Create a non-proto file
        let mut txt_file = fs::File::create(proto_dir.join("readme.txt")).unwrap();
        writeln!(txt_file, "This is not a proto file").unwrap();

        let found_files = find_proto_files(&proto_dir).unwrap();
        assert_eq!(found_files.len(), 2);
        assert!(found_files
            .iter()
            .any(|p| p.file_name().unwrap() == "test1.proto"));
        assert!(found_files
            .iter()
            .any(|p| p.file_name().unwrap() == "test2.proto"));
    }
}
