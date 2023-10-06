prompt_template_3 = """
Generate a unit test for the following method:
Method: {method_name}
Class: {class_name}
Package: {package}
Imports: 
{imports}

Method code: 
```java
{method_code}
```

This is the constructor of the class in which the method is defined:
```java
{class_header}
```

Here is some additional code that might be useful:

Related methods: 

{related_methods}

[\\INST]

[AI]:
"""