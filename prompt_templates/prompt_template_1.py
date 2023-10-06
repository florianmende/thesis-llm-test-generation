# This prompt contains the following information:
# - Method name
# - Class name
# - Package name
# - Imports
# - Method code

prompt_template_1 = """
Write a unit test for the following method:
Method: {method_name}
Class: {class_name}
Package: {package}
Imports: 
{imports}

Method code: 
```java
{method_code}
```

[\\INST]

[AI]:
"""