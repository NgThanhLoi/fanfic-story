"""
Dedicated Fandom Knowledge Base for 'Nhất Thế Chi Tôn' (一世之尊)
Author: Cuttlefish That Loves Diving (Ái Tiềm Thủy Đích Ô Tặc)
"""

from typing import Dict, List
from fanfic_pipeline.core.models import CharacterVoice

REALMS = {
    "Trúc Cơ": "Bách Nhật Trúc Cơ, rèn luyện gân cốt khí huyết, tích lũy nội lực sơ khai.",
    "Tích Khí": "Tụ khí đan điền, đả thông kinh mạch kỳ kinh bát mạch.",
    "Khai Khiếu": "Mở cửu khiếu (Mắt, Tai, Mũi, Miệng, Tiền Âm, Hậu Âm). Tề Khiếu là viên mãn, bắt đầu cảm ứng thiên địa.",
    "Bán Bộ Ngoại Cảnh": "Nội cảnh sơ thành, cảm ứng nội ngoại giao hòa, nắm giữ sát chiêu sơ bộ.",
    "Ngoại Cảnh": "Thiên Nhân Hợp Nhất, dẫn động thiên địa nguyên khí, phân 1 đến 9 Trọng Thiên. Đỉnh phong là Thiên Tiên Bán Bộ.",
    "Pháp Thân": "Thoát phàm nhập thánh, ngưng tụ Pháp Thân (Địa Tiên -> Thiên Tiên).",
    "Truyền Thuyết": "Vô Sở Bất Tri, lưu lại truyền thuyết chư thiên, hình chiếu vạn giới.",
    "Tạo Hóa": "Khổ hải trầm luân, cải tạo chư thiên, nắm giữ quy tắc đại đạo.",
    "Bỉ Ngạn": "Đứng trên dòng thời gian, nắm giữ Đạo Quả, hồi tố quá khứ, nhìn thấu tương lai."
}

CHARACTER_VOICES: Dict[str, CharacterVoice] = {
    "meng_qi": CharacterVoice(
        character_id="meng_qi",
        name="Mạnh Kỳ",
        aliases=["Chân Định", "Cuồng Đao Tô Mạnh", "Tô Tử Viễn", "Tiểu Hòa Thượng", "Lôi Đao Cuồng Tăng"],
        gender="Nam",
        personality_core="Bên ngoài thích 'trang bức', miệng lưỡi sắc bén, hay trêu đùa tự giễu; bên trong vô cùng trọng tình nghĩa, kiên định bất khuất, có nỗi sợ sâu sắc nhưng không bao giờ chịu khuất phục trước sự thao túng của Lục Đạo và số phận.",
        lexicon_rules=[
            "Thường tự xưng 'Bần tăng' (khi còn là hòa thượng) hoặc xưng 'Ta', 'Tại hạ', xưng hô bằng hữu thân mật.",
            "Hay nói câu trêu đùa: 'Nhân sinh hà xứ bất tương phùng', 'Mạnh mỗ đao pháp tuyệt luân', tự khen mình anh tuấn tiêu sái.",
            "Cấm kỵ: Tuyệt đối không làm ra vẻ thánh mẫu đạo đức giả, không yếu đuối cầu xin kẻ thù, không phản bội đồng đội dù phải trả giá bằng mạng sống."
        ],
        dialogue_rhythm="Nhanh, dí dỏm, biến hóa linh hoạt. Khi đùa giỡn thì lươn lẹo nghịch ngợm, khi chiến đấu hoặc đối mặt biến cố lớn thì lời ít mà ý nhiều, đanh thép lạnh lùng.",
        micro_behaviors=[
            "Vô thức sờ lên đầu trọc (khi mới hoàn tục)",
            "Tay phải nhẹ nhàng đặt lên chuôi đao hoặc khẽ siết chặt đao ý",
            "Khóe môi khẽ nhếch lên nụ cười nửa đùa nửa thật để che giấu sự căng thẳng",
            "Mắt lóe lên tia sáng cơ trí khi phát hiện ra điểm mấu chốt của nhiệm vụ Luân Hồi"
        ],
        moral_boundaries="Tuyệt đối bảo vệ đồng đội trong tiểu đội Luân Hồi (Chỉ Vi, Chính Ngôn, Ngọc Thư, Triệu Hằng). Không lạm sát kẻ vô tội, nhưng với kẻ địch mưu hại mình thì dứt khoát trảm thảo trừ căn.",
        secret_motive="Chặt đứt dây rối Lục Đạo Luân Hồi Chi Chủ, tìm ra sự thật về thân thế và giải thoát bản thân khỏi bàn cờ của các đại năng Bỉ Ngạn."
    ),
    "jiang_zhiwei": CharacterVoice(
        character_id="jiang_zhiwei",
        name="Giang Chỉ Vi",
        aliases=["Chỉ Vi muội muội", "Kiếm Xuất Vô Hối", "Tẩy Kiếm Các truyền nhân"],
        gender="Nữ",
        personality_core="Kiếm tâm thuần túy, phóng khoáng hào sảng, trọng nghĩa khinh sinh. Không hề có chút ủy mị của nữ nhi thông thường, coi kiếm như mạng, dám yêu dám hận, quang minh lỗi lạc.",
        lexicon_rules=[
            "Xưng 'Ta', gọi Mạnh Kỳ là 'Tiểu hòa thượng' hoặc 'Mạnh Kỳ', gọi các bạn khác thân mật chân thành.",
            "Lời nói trực diện, thẳng thắn, không vòng vo, mang phong thái hiệp khách.",
            "Cấm kỵ: Không nói lời hoa mỹ sáo rỗng, không bao giờ lộ vẻ do dự yếu đuối khi rút kiếm."
        ],
        dialogue_rhythm="Tự tin, trong trẻo, dứt khoát như tiếng kiếm reo. Luôn mang lại cảm giác an tâm và chỗ dựa vững chắc cho đồng đội.",
        micro_behaviors=[
            "Ngón tay khẽ chạm vào bảo kiếm bên hông",
            "Ánh mắt sáng rực như kiếm quang mỗi khi gặp đối thủ mạnh",
            "Khẽ mỉm cười bất đắc dĩ nhưng đầy ấm áp trước những trò đùa của Mạnh Kỳ"
        ],
        moral_boundaries="Kiếm hạ phân biệt rõ thiện ác. Kiếm xuất vô hối (kiếm đã rút thì không hối hận), sẵn sàng hy sinh để mở đường máu cho đồng đội.",
        secret_motive="Theo đuổi cảnh giới tối cao của Kiếm Đạo, chứng minh kiếm tâm không thẹn với trời đất."
    ),
    "gu_xiaosang": CharacterVoice(
        character_id="gu_xiaosang",
        name="Cố Tiểu Tang",
        aliases=["Tiểu Tang", "Yêu Nữ", "Tố Nữ Đạo Thánh Nữ", "Vô Thượng Thiên Ma"],
        gender="Nữ",
        personality_core="Cực kỳ thông minh, giảo hoạt khó lường, miệng cười hoa nở nhưng tâm cơ thâm sâu như biển. Luôn giấu kín nỗi tuyệt vọng và bi kịch bên dưới vẻ ngoài quyến rũ tinh quái.",
        lexicon_rules=[
            "Thường gọi Mạnh Kỳ là 'Tướng công' (相公) hoặc 'Nhỏ hòa thượng' với giọng điệu nửa đùa cợt nửa chân thành.",
            "Lời nói lấp lửng, chứa nhiều tầng nghĩa ẩn ý, thích dùng ẩn dụ và trêu chọc tâm lý đối phương.",
            "Cấm kỵ: Không bao giờ để lộ sự yếu đuối hay hoảng loạn trước mặt kẻ khác."
        ],
        dialogue_rhythm="Mềm mại, ma mị, lúc như gió thoảng bên tai, lúc lại như lưỡi dao sắc bén đâm trúng tim đen.",
        micro_behaviors=[
            "Khẽ nghiêng đầu cười khẽ, đuôi mắt cong cong mang vẻ yêu kiều ma mị",
            "Ngón tay ngọc ngà vân vê dải lụa trắng hoặc lọn tóc",
            "Trong khoảnh khắc không ai để ý, đáy mắt thoáng qua vẻ cô tịch và tuyệt vọng đến thấu xương"
        ],
        moral_boundaries="Hành sự theo quy tắc tàn nhẫn của Ma Đạo, nhưng với Mạnh Kỳ luôn có một sợi dây liên kết vừa muốn lợi dụng vừa muốn cùng nhau phá vỡ lồng giam số phận.",
        secret_motive="Chống lại sự đồng hóa của Kim Mẫu / Vô Sinh Lão Mẫu, tìm kiếm một tia sinh cơ duy nhất để trở thành một cá thể độc lập."
    ),
    "qi_zhengyan": CharacterVoice(
        character_id="qi_zhengyan",
        name="Tề Chính Ngôn",
        aliases=["Tề sư huynh", "Mặt đơ", "Ma Hoàng truyền nhân"],
        gender="Nam",
        personality_core="Mặt lạnh như băng, ít nói kiệm lời, bề ngoài bình thường nhưng nội tâm ẩn chứa lý tưởng cải tạo thế giới vĩ đại và khát vọng bình đẳng sâu sắc.",
        lexicon_rules=[
            "Nói ngắn gọn, súc tích, chỉ nói đúng trọng tâm.",
            "Không bao giờ than vãn hay bộc lộ cảm xúc thừa thãi.",
            "Cấm kỵ: Không tự cao tự đại, không khinh thường kẻ yếu thế."
        ],
        dialogue_rhythm="Trầm ổn, bình thản, nhịp điệu chậm rãi và chắc chắn.",
        micro_behaviors=[
            "Khuôn mặt ngàn năm không đổi sắc (mặt đơ kinh điển)",
            "Lẳng lặng đứng sau lưng bảo vệ các vị trí yếu hại của đồng đội",
            "Nhìn phàm nhân đau khổ với ánh mắt thâm trầm suy tư"
        ],
        moral_boundaries="Chấp nhận gánh chịu mọi tiếng xấu Ma đạo để mở ra con đường tu luyện công bằng cho muôn vàn chúng sinh nghèo khổ.",
        secret_motive="Thực hiện lý tưởng 'Mọi người đều có thể tu luyện, chúng sinh bình đẳng', phá bỏ ách thống trị độc quyền của thế gia và môn phái lớn."
    ),
    "ruan_yushu": CharacterVoice(
        character_id="ruan_yushu",
        name="Nguyễn Ngọc Thư",
        aliases=["Ngọc Thư", "Lang Nha Nguyễn Thị"],
        gender="Nữ",
        personality_core="Thanh nhã như tiên, bên ngoài lãnh đạm thanh cao, nhưng thực chất là một 'tín đồ ẩm thực' (thích ăn bánh ngọt, cá khô, thịt nướng), ngoài lạnh trong nóng.",
        lexicon_rules=[
            "Thường chỉ trả lời bằng những từ đơn: 'Ừ', 'Biết rồi', 'Ngon', 'Muốn ăn'.",
            "Khi nói về âm luật hoặc mỹ thực thì đôi mắt sáng rực và nói nhiều hơn một chút."
        ],
        dialogue_rhythm="Ngắn gọn, thanh nhã, âm điệu êm tai như tiếng đàn Cổ Cầm.",
        micro_behaviors=[
            "Lén lút lấy đồ ăn vặt hoặc cá khô giấu trong tay áo ra ăn khi không ai để ý",
            "Ôm đàn Phượng Tê bên người, ngón tay nhẹ vuốt ve dây đàn",
            "Khẽ gật đầu tỏ vẻ đồng tình khi Mạnh Kỳ đề xuất đi ăn quán ngon"
        ],
        moral_boundaries="Tuyệt đối trung thành với tình bạn tiểu đội Luân Hồi, dùng tiếng đàn bảo hộ đồng đội.",
        secret_motive="Vượt qua gông xiềng của gia tộc và quy định hà khắc của thế gia."
    )
}

LUC_DAO_RULES = """
QUY TẮC KHÔNG GIAN LỤC ĐẠO LUÂN HỒI:
1. Nghiêm cấm tiết lộ sự tồn tại của Lục Đạo Luân Hồi cho bất kỳ ai không phải thành viên Luân Hồi (Vi phạm: Xóa sổ linh hồn).
2. Hoàn thành nhiệm vụ nhận được Thiện Công (Điểm đổi thưởng).
3. Thiện Công có thể đổi: Công pháp (Như Lai Thần Chưởng, Tiệt Thiên Thất Kiếm, Bát Cửu Huyền Công), Thần binh, Đan dược, Thông tin tình báo.
4. Nếu số dư Thiện Công âm sau nhiệm vụ: Bị Lục Đạo xóa sổ hoặc đưa vào Nhiệm vụ trừng phạt có tỷ lệ tử vong 99%.
5. Cảnh giới thực tế tại Chân Thực Giới liên kết chặt chẽ với thực lực trong không gian Luân Hồi.
"""
