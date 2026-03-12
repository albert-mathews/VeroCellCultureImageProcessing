import subprocess
import sys
import os

# Default LaTeX file (change if needed)
LATEX_FILE = 'paper/paper.tex'  # Your LaTeX source file relative to root
PDF_OUTPUT_DIR = 'paper'  # Directory for output PDF
PDF_OUTPUT = os.path.join(PDF_OUTPUT_DIR, 'Vero Cell Culture Morphology Detection Benchmarking.pdf')  # Compiled PDF

def compile_latex(tex_file=LATEX_FILE):
    """Compile LaTeX to PDF using pdflatex (non-interactive)."""
    try:
        # Ensure output dir exists
        os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
        
        # Run pdflatex twice for full compilation (handles refs, TOC)
        for _ in range(2):
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-file-line-error',
                 f'-output-directory={PDF_OUTPUT_DIR}', tex_file],
                capture_output=True,
                text=True,
                check=True
            )
            print(result.stdout)  # Show compilation output/warnings
        
        # pdflatex outputs <basename>.pdf, so rename if needed (from paper.pdf to custom name)
        default_pdf = os.path.join(PDF_OUTPUT_DIR, 'paper.pdf')
        if os.path.exists(default_pdf):
            os.rename(default_pdf, PDF_OUTPUT)
        
        print(f"Successfully compiled {tex_file} to {PDF_OUTPUT}.")
        return True
    except subprocess.CalledProcessError as e:
        print("Compilation failed! Check errors below:")
        print(e.stdout)  # Warnings
        print(e.stderr)  # Errors
        return False

if __name__ == '__main__':
    # Optional: Take file name from command line (e.g., python compile_latex.py myfile.tex)
    if len(sys.argv) > 1:
        tex_file = sys.argv[1]
    else:
        tex_file = LATEX_FILE
    
    compile_latex(tex_file)