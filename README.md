# LTHD_DiaDiemAnUong
Project Quản lý Địa điểm ăn uống phát triển backend với Django Rest Framework và frontend với ReactJS. Chứng thực và phân quyền phải thực hiện thông qua OAuth2.
  - Đăng nhập (các vai trò người quản trị, người dùng cá nhân hoặc người dùng cửa hàng).
  - Đăng ký vai trò người dùng cá nhân hoặc cửa hàng ăn uống (phải có avatar). Đăng ký người dùng là một cửa hàng cần được xác nhận của người quản trị thì tài khoản mới được kích hoạt, mỗi tài khoản cửa hàng yêu cầu hiển thị địa điểm cửa hàng thông qua bản đồ google map.
  
  - Người dùng cá nhân được phép thực hiện tra cứu món ăn linh hoạt theo tên, giá, loại thức ăn và cửa hàng mong muốn.
  - Người dùng được phép đặt món ăn trực tiếp qua hệ thống và được phép chọn thực hiện thanh toán trực tuyến (dùng paypal hoặc stripe hoặc momo hoặc zalo pay) hoặc thanh toán tiền mặt, chú ý tiền thanh toán bao gồm tiền thức ăn và tiền vận chuyển tuỳ quy định từng cửa hàng.
  - Cho phép người dùng theo dõi cửa hàng, mỗi khi cửa hàng đăng menu thức ăn hoặc đăng món ăn mới thì người dùng sẽ nhận được email hoặc sms thông báo.
   - Người dùng được phép bình luận và đánh giá món ăn và các cửa hàng.
  
  - Cửa hàng được phép đăng món ăn hoặc menu thức ăn theo từng buổi, mỗi món ăn có thể thiết thiết lập thời điểm bán trong ngày hoặc trạng thái món ăn (còn hay hết). Cửa hàng được phép xác nhận đơn hàng và ghi nhận giao hàng khi nhận đơn đặt từ khách hàng.
  - Cửa hàng được phép xem thống kê doanh thu các sản phẩm, danh mục sản phẩm theo tháng, quý và năm.
  
  - Người quản trị có thể xem thống kê tần suất bán hàng, tổng sản phẩm kinh doanh của các cửa hàng theo tháng, quý, năm (có thể phát triển thống kê này linh hoạt hơn để các quản trị có thể quản lý tốt hơn). 
