C hoàn tất6 candidate độc lập (3/model), không feedback giữa candidate.12B và31B đều0/3 public passes; candidate được chọn của mỗi model đều qua67 test chức năng nhưng không đạt performance grader độc lập. Không có truncation.

Dù dùngtemperature0.6 và3 seeds khác nhau, các patch đều xoay quanh thêm whitespace quantifier/lazy quantifier;12B có một candidate thêmDOTALL. Chưa tạo được đa dạng ở mức thuật toán. Lựa chọn public runtime chỉ xếp hạng các phương án vẫn sai; không biến phương án nhanh nhất trong nhóm sai thành bản sửa đạt.

So với A/B, C dùng cùng trần4608 generated tokens/model nhưng temperature khác, không có context feedback và actual token thấp hơn nhiều; không kết luận chiến lược độc lập vô ích. Một task công khai đã được quan sát, không có estimate thành công trên tập issue rộng. Independent grader không tham gia lựa chọn, không chọn lại sau khi thấy hidden outcome.
