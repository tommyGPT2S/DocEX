# Custom Processor Example

This example demonstrates how to create and use a custom processor outside the main DocEX package.

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
   - This allows DocEX to use your custom processor for PDF files
   - No need to modify the main DocEX package

3. **Usage**
   - The example script demonstrates:
     - Patching the processor mapping
     - Creating a DocEX instance
     - Adding a PDF document
     - Processing the document with the custom processor
     - Displaying the results

## Running the Example

1. Make sure you have the required dependencies:
   ```sh
   pip install pdfminer.six pydocex
   ```

2. Run the example:
   ```sh
   python run_custom_pdf_processor.py
   ```

## Notes

- The custom processor is registered dynamically at runtime
- It will be used for all PDF files processed by DocEX
- The processor can be modified without changing the main package
- Multiple custom processors can be registered for different file types