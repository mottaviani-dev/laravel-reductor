"""Unit tests for PHP tokenizer."""

import pytest
from ml.core.tokenizer import PHPTokenizer, extract_test_name


class TestPHPTokenizer:
    """Test cases for PHPTokenizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tokenizer = PHPTokenizer()
    
    def test_tokenize_simple_code(self):
        """Test tokenizing simple PHP code."""
        code = """
        <?php
        function testUserCanLogin() {
            $user = new User();
            $this->assertTrue($user->login());
        }
        """
        
        tokens = self.tokenizer.tokenize(code)
        
        assert 'testusercanlogin' in tokens
        assert 'user' in tokens
        assert 'login' in tokens
        assert 'asserttrue' in tokens
    
    def test_remove_comments(self):
        """Test comment removal."""
        code = """
        // This is a comment
        function test() {
            /* Multi-line
               comment */
            return true; # Shell comment
        }
        """
        
        cleaned = self.tokenizer._remove_comments(code)
        
        assert 'comment' not in cleaned.lower()
        assert 'function test()' in cleaned
        assert 'return true;' in cleaned
    
    def test_extract_assertions(self):
        """Test extraction of assertion keywords."""
        code = """
        $this->assertEquals($expected, $actual);
        $this->assertNull($value);
        $this->expectException(RuntimeException::class);
        """
        
        tokens = self.tokenizer.tokenize(code)
        
        assert 'assertequals' in tokens
        assert 'assertnull' in tokens
        assert 'expectexception' in tokens
    
    def test_camel_case_splitting(self):
        """Test splitting of camelCase words."""
        code = "getUserByEmail"
        
        tokens = self.tokenizer.tokenize(code)
        
        assert 'get' in tokens
        assert 'user' in tokens
        assert 'by' in tokens
        assert 'email' in tokens
        assert 'getuserbyemail' in tokens  # Original also included
    
    def test_snake_case_splitting(self):
        """Test splitting of snake_case words."""
        code = "test_user_can_create_post"
        
        tokens = self.tokenizer.tokenize(code)
        
        assert 'test' in tokens
        assert 'user' in tokens
        assert 'can' in tokens
        assert 'create' in tokens
        assert 'post' in tokens
    
    def test_stop_words_filtering(self):
        """Test filtering of stop words."""
        code = "the user is in the system and can do this"
        
        tokens = self.tokenizer.tokenize(code)
        
        # Stop words should be filtered
        assert 'the' not in tokens
        assert 'is' not in tokens
        assert 'and' not in tokens
        assert 'can' not in tokens
        
        # Content words should remain
        assert 'user' in tokens
        assert 'system' in tokens
    
    def test_empty_input(self):
        """Test handling of empty input."""
        tokens = self.tokenizer.tokenize("")
        assert tokens == []
    
    def test_no_lowercase_option(self):
        """Test tokenization without lowercase conversion."""
        code = "TestUserLogin"
        
        tokens = self.tokenizer.tokenize(code, lowercase=False)
        
        assert 'TestUserLogin' in tokens
        assert 'Test' in tokens
        assert 'User' in tokens
        assert 'Login' in tokens


class TestExtractTestName:
    """Test cases for extract_test_name function."""
    
    def test_extract_from_file_path(self):
        """Test extraction from file paths."""
        assert extract_test_name("/path/to/UserTest.php") == "User"
        assert extract_test_name("tests/Unit/AuthTest.php") == "Auth"
        assert extract_test_name("SomeTest.php") == "Some"
    
    def test_extract_from_class_method(self):
        """Test extraction from Class::method format."""
        assert extract_test_name("UserTest::testCanLogin") == "testCanLogin"
        assert extract_test_name("App\\Tests\\UserTest::test_login") == "test_login"
    
    def test_extract_from_hash_format(self):
        """Test extraction from Test#method format."""
        assert extract_test_name("UserTest#testCreate") == "testCreate"
        assert extract_test_name("AuthTest#test_logout") == "test_logout"
    
    def test_extract_from_at_format(self):
        """Test extraction from Test@method format."""
        assert extract_test_name("UserTest@testUpdate") == "testUpdate"
        assert extract_test_name("PostTest@test_delete") == "test_delete"
    
    def test_complex_paths(self):
        """Test extraction from complex paths."""
        assert extract_test_name("/var/www/app/tests/Unit/UserTest.php") == "User"
        assert extract_test_name("C:\\project\\tests\\FeatureTest.php") == "Feature"
    
    def test_no_match(self):
        """Test handling of non-matching inputs."""
        assert extract_test_name("not_a_test") == "not_a_test"
        assert extract_test_name("") is None


if __name__ == '__main__':
    pytest.main([__file__])