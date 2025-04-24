use sha2::{Sha256, Digest};

pub type Hash = String;

pub fn calculate_hash(data: &str) -> Hash {
    let mut hasher = Sha256::new();
    hasher.update(data.as_bytes());
    let result = hasher.finalize();
    hex::encode(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_hash() {
        let data = "test data";
        let hash = calculate_hash(data);

        // SHA-256 hash for "test data" 
        let expected = "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9";
        assert_eq!(hash, expected);
    }
} 