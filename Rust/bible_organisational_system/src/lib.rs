pub mod internals;
//pub mod utils;
pub mod python_bindings;


pub fn add(left: u64, right: u64) -> u64 {
    left + right
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn local_lib_add_function_works() {
        let result = add(2, 2);
        assert_eq!(result, 4);
    }
}
