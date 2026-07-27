# Quy ước file CSV glossary

## Encoding
- **UTF-8 KHÔNG BOM** (Windows Notepad hay tự thêm BOM → tắt đi)

## Cấu trúc cột
| Cột | Bắt buộc | Giá trị | Mô tả |
|-----|----------|---------|-------|
| `source` | Có | text | Từ/cụm gốc (EN/ZH/...) |
| `target` | Có | text | Bản dịch tiếng Việt |
| `type` | Có | `character` \| `term` \| `place` \| `phrase` | Loại thuật ngữ |
| `note` | Không | text | Ghi chú cho người dịch |
| `genre` | Có | slug | Thể loại (khớp `glossary/genres/<genre>.csv`) |
| `book` | Không | slug | Cuốn cụ thể (rỗng = áp dụng cả thể loại) |

## Quy tắc escape (RẤT QUAN TRỌNG)
- **Dấu phẩy** trong bất kỳ trường nào → bọc trong dấu nháy kép: `"thuật ngữ, phổ biến"`
- **Dấu nháy kép** trong trường → escape bằng cách nhân đôi: `""text""`
- **Dòng trống** → KHÔNG có; mỗi dòng là 1 thuật ngữ
- **Giá trị rỗng** → để trống giữa 2 dấu phẩy: `,,`

## Ví dụ file chuẩn
```csv
source,target,type,note,genre,book
张伟,Trương Vĩ,character,Nhân vật chính,tien-hiep,san-ti
修仙,Tu tiên,term,"thuật ngữ tu chân, phổ biến",tien-hiep,san-ti
灵气,Linh khí,term,,tien-hiep,
API,API,term,Giữ nguyên EN,ky-thuat-it,
```

## Đọc file bằng Python
```python
import pandas as pd
df = pd.read_csv("glossary/_template.csv", encoding="utf-8")
# df.columns = ['source', 'target', 'type', 'note', 'genre', 'book']
```

## Validate
Dùng `scripts/glossary_qa.py` (khi chạy nó) sẽ tự kiểm tra format CSV.
