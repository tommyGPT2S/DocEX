# Custom Processor Example

This example demonstrates how to create and use a custom processor outside the main DocFlow package.

## Files

- `my_pdf_text_processor.py`: A custom PDF text extraction processor using pdfminer.six
- `run_custom_pdf_processor.py`: Example script showing how to use the custom processor and register dynamically with mapping rules.

## How It Works

1. **Custom Processor Implementation**
   - The processor is defined in its own file
   - It inherits from `BaseProcessor`
   - Implements `can_process()` and `process()` methods
   - Uses pdfminer.six for PDF text extraction.
   - Includes layout analysis for better text extraction

2. **Processor Factory Mapping (Dynamic Rule)**
   - The example shows how to patch the processor factory mapping by adding a rule to `factory.mapper.rules`:
   
   ```python
   from docflow.processors.factory import factory
   from my_pdf_text_processor import MyPDFTextProcessor
   
   def pdf_rule(document):
       if document.name.lower().endswith('.pdf'):
           return MyPDFTextProcessor
       return None
   
   factory.mapper.rules.insert(0, pdf_rule)  # Highest priority
   ```
   - This allows DocFlow to use your custom processor for PDF files
   - No need to modify the main DocFlow package

3. **Usage**
   - The example script demonstrates:
     - Patching the processor mapping
     - Creating a DocFlow instance
     - Adding a PDF document
     - Processing the document with the custom processor
     - Displaying the results

## Running the Example

1. Make sure you have the required dependencies:
   ```sh
   pip install pdfminer.six pydocflow
   ```

2. Run the example:
   ```