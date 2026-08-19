package type_error

// BrokenFunction intentionally returns a string literal for an int return type to trigger a type-checker diagnostic.
func BrokenFunction() int {
	return "invalid string return"
}
