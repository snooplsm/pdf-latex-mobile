use std::io::{self, Read};
fn main() {
    let mut request = String::new();
    io::stdin()
        .read_to_string(&mut request)
        .expect("read request JSON from stdin");
    let result = latex_mobile::compile_json(&request);
    println!("{result}");
    let response: latex_mobile::Response = serde_json::from_str(&result).unwrap();
    if !response.ok {
        std::process::exit(1);
    }
}
