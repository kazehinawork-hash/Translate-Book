using System.Collections.Generic;

namespace TranslateBook.Models
{
    public class TocItem
    {
        public string Title { get; set; } = "";
        public string FilePath { get; set; } = "";
        public string Anchor { get; set; } = "";
        public List<TocItem> NestedItems { get; set; } = new();
    }
}
