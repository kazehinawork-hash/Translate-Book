@echo off
chcp 65001 >nul
echo ===================================================
echo   CAI DAT MOI TRUONG CHO DU AN TRANSLATE BOOK
echo ===================================================
echo.

REM 1. Kiểm tra Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [LOI] Khong tim thay Python! Vui long cai dat Python 3.10+ va tick vao "Add to PATH" khi cai dat.
    pause
    exit /b
)

REM 2. Tạo .venv nếu chưa có
IF NOT EXIST ".venv" (
    echo [1/4] Dang tao moi truong ao .venv...
    python -m venv .venv
) ELSE (
    echo [1/4] Moi truong .venv da ton tai. Bo qua buoc tao.
)

REM 3. Kích hoạt .venv và cài requirements.txt
echo [2/4] Dang cai dat cac thu vien co ban tu requirements.txt... (Vui long doi vai phut)
call .\.venv\Scripts\activate.bat
pip install -r requirements.txt

REM 4. Hỏi cài GPU
echo.
echo ===================================================
echo [3/4] KIEM TRA CARD MAN HINH (GPU)
echo ===================================================
echo May tinh cua ban co Card man hinh NVIDIA khong?
echo N - Khong co (Chi chay CPU, phu hop cho laptop van phong)
echo Y - Co (Cai ban GPU sieu toc, nang khoang 4GB)
set /p has_gpu="Chon Y hoac N: "

if /I "%has_gpu%"=="Y" (
    echo.
    echo [4/4] Dang cai dat PyTorch va PaddlePaddle phien ban GPU...
    echo - Dang xoa ban CPU mac dinh (Neu co)...
    pip uninstall torch paddlepaddle -y
    
    echo - Dang tai ban GPU (Buoc nay tai rat nang, tuy mang, co the mat 10-20 phut. DUNG TAT CUA SO!)...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    pip install paddlepaddle-gpu
    
    echo.
    echo [XONG] Da cai dat thanh cong phien ban GPU!
) else (
    echo.
    echo [4/4] Ban da chon N. Bo qua cai dat GPU. Du an se tiep tuc chay bang CPU.
)

echo.
echo ===================================================
echo TAT CA DA XONG! BAN CO THE DONG CUA SO NAY.
echo Bay gio ban chi can bam vao scripts\translate.bat de bat dau dich sach.
echo ===================================================
pause
