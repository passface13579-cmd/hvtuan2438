def tao_tuple_tu_list(lst):
    return tuple(lst)


# Nhập danh sách từ người dùng và xử lý chuỗi
input_list = input("Nhap danh sach cac so, cach nhau bang dau phay: ")
numbers = list(map(int, input_list.split(',')))

my_tuple = tao_tuple_tu_list(numbers)
print("List:", numbers)
print("Tuple từ List:", my_tuple)
