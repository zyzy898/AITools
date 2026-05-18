# coding:utf-8

import torch.cuda
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
import pickle
from zhipuai import ZhipuAI
import os
import pandas as pd
import time
import gradio as gr
import random
import shutil
import  jieba.analyse as aly
from collections import Counter
from pymilvus import MilvusClient,CollectionSchema,FieldSchema,DataType
from pypinyin import lazy_pinyin
from tqdm import tqdm
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import faiss

def get_ans(prompt,model="glm-4-plus"):
    client = ZhipuAI(api_key="0f56bcd3ce36d22b5b6564de4faeebfe.nvc4AlZb8rw1WhFG")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        top_p=0.7,
        temperature=0.9,
        max_tokens=2048,
        stream=True,
    )
    # ans = ""
    # for trunk in response:
    #     ans += trunk.choices[0].delta.content
    # return ans
    return response

def document_summary_20(documents):
    new_content = []
    for document in documents:
        content = document.page_content

        batch = 10000
        chunk_overlap = 300
        if len(content) > batch:
            for i in tqdm(range(0,len(content),batch),desc="长文档总结中"):
                temp_c = content[max(0,i-chunk_overlap):i+batch]
                prompt = f"以下文字主要讲了什么内容，使用20个字回复，无需输出其他内容：\n```{temp_c}```\n以上文字主要讲了什么内容，使用20个字回复，无需输出其他内容："
                # print("")
                resp = get_ans(prompt,model="glm-4-flashx")
                ans = ""
                for trunk in resp:
                    ans += trunk.choices[0].delta.content
                new_content.append(ans)
                print(ans)
    return new_content

def document_summary(documents):
    new_content = []
    for document in documents:
        content = document.page_content

        batch = 10000
        chunk_overlap = 300
        if len(content) > batch:
            for i in tqdm(range(0,len(content),batch),desc="长文档总结中"):
                temp_c = content[max(0,i-chunk_overlap):i+batch]
                prompt = f"```{temp_c}```\n总结以上内容："
                # print("")
                resp = get_ans(prompt,model="glm-4-flashx")
                ans = ""
                for trunk in resp:
                    ans += trunk.choices[0].delta.content
                new_content.append(ans)
                print(ans)
    return new_content

def merge_summary(s1,s2):
    s1_emb = emb_model.to_emb(s1)

    text1 = []
    text2 = []

    for i in range(len(s1)):
        if i == 0:
            text1.append(s1[0])
            text2.append(s2[0])
        else:
            sim = cosine_similarity(s1_emb[i:i+1],s1_emb[i-1:i])
            if sim > 0.9:
                text2[-1] += s2[i]
            else:
                text1.append(s1[i])
                text2.append(s2[i])
    return text1,text2

class MyDocument():
    def __init__(self,dir,name):
        loader = DirectoryLoader(dir)
        documents = loader.load()
        summarys1 = document_summary_20(documents)
        summarys2 = document_summary(documents)

 #        summarys1 = ['樱桃根系、叶片、花果等特征及病虫害防治。',
 #         '樱桃病虫害防治方法及症状描述。',
 #         '樱桃病虫害防治及虫害介绍。',
 #         '果树病虫害防治方法详述。',
 #         '金龟子种类及防治方法，樱桃栽培管理措施。',
 #         '温室大棚樱桃种植技术及管理',
 #         '樱桃树修剪技术及树形培养',
 #         '樱桃树修剪、品种特性及采后管理。',
 #         '樱桃品种特性及栽培技术',
 #         '温室大棚樱桃栽培技术及管理要点',
 #         '温室大棚建造、设计及附属设施。',
 #         '番茄生物学特征及生长发育周期。',
 #         '介绍番茄的优良品种及其特性。',
 #         '介绍了多种番茄品种的特性和育苗技术。',
 #         '穴盘育苗技术及其应用和操作要点。',
 #         '番茄种植技术及管理要点',
 #         '番茄种植技术及管理要点',
 #         '番茄种植技术及病虫害防治',
 #         '番茄栽培技术及常见病害防治',
 #         '番茄病害种类及防治方法。',
 #         '番茄病害种类及防治方法。',
 #         '番茄病虫害防治方法及注意事项。',
 #         '介绍了美洲斑潜蝇、蚜虫、茶黄螨、蝼蛄的形态特征、生活习性和防治方法。']
 #
 #        summarys2 = ['这份文档详细介绍了樱桃的各个器官特征、年生长发育周期、移栽与管理以及主要病虫害及防治方法。\n\n**主要内容包括**：\n\n1. **器官特征**：\n   - **根系**：负责吸收水分和营养，分为实生根和茎原根，根系深度和发育程度受土壤和肥水管理影响。\n   - **叶片**：进行光合作用，合成有机营养，叶片大小和厚度影响果实品质。\n   - **花与花芽**：每个花芽孕育1-5朵花，花朵结构包括雄蕊、雌蕊、花瓣、花萼和花柄，授粉主要依靠蜜蜂、风力和重力。\n   - **果实**：易裂果，果实发育期较短，分为速长期、硬核期和第二次速长期。\n   - **叶芽**：分为顶叶芽和侧叶芽，具有早熟性。\n   - **枝**：分为发育枝和结果枝，结果枝包括混合枝、长果枝、中果枝、短果枝和花束状果枝。\n\n2. **年生长发育周期**：\n   - **萌芽和开花**：温度敏感，花期分为初花期、盛花期和落花期。\n   - **新梢生长**：与果实发育交互进行，分为速长期和缓慢生长期。\n   - **果实发育**：分为速长期、硬核期和第二次速长期，果实成熟时颜色和可溶性固形物含量发生变化。\n   - **花芽分化**：在幼果期开始，分化时间早，分化速度快。\n   - **落叶与休眠**：落叶发生在霜冻前后，树体进入休眠期。\n\n3. **移栽与管理**：\n   - **幼苗移栽与管理**：株行距、移栽时期、幼苗处理、配置授粉品种和种植后管理等。\n   - **大树移栽方法与种植后的管理**：树体选择、种植前的准备、移栽方法、种植后管理等。\n\n4. **主要病虫害及防治方法**：\n   - **叶斑病**：主要危害叶片，症状为紫色斑点，最终形成褐色穿孔。\n   - **灰霉病**：主要危害幼果、叶片或成熟果实，症状为水渍状，表面密生灰色霉层。\n   - **根瘤病**：主要发生在根颈、根系上及嫁接口处，症状为灰白色瘤状物。\n\n**总结**：\n\n樱桃的栽培和管理需要综合考虑各个器官的特征、生长发育周期、移栽与管理以及病虫害防治等方面，才能保证樱桃的生长发育和产量。',
 # '以上内容详细介绍了樱桃树常见的多种病害及其防治方法，以下是对这些内容的总结：\n\n1. **樱桃黑斑病**：由链格孢菌引起，主要危害果实，表现为果实表面形成黑色病斑和轮纹，严重时会导致果园绝产。防治方法包括清除病果、科学管理果园和药剂防治。\n\n2. **炭疽病**：主要危害果实、叶片和枝梢，表现为果实表面出现暗绿色斑点，病斑扩大后使果实变黑、收缩变形。防治方法包括冬季清园、加强果园管理和药剂防治。\n\n3. **细菌性穿孔病**：主要危害叶片、新梢和果实，表现为叶片出现淡褐色或灰白色斑点，后扩大成圆形、多角形或不规则形病斑。防治方法包括农业防治和化学防治。\n\n4. **褐腐病**：又称灰星病，主要危害花和果实，表现为花器变褐色、干枯，果实出现黑褐色斑点，后蔓延引起整果软腐。防治方法包括农业防治和化学防治。\n\n5. **煤污病**：主要危害叶片、枝条和果实，表现为叶面出现霉点，严重时布满叶、枝及果面。防治方法包括农业防治和化学防治。\n\n6. **流胶病**：主要危害枝干，表现为枝干伤口处溢泌树胶，病部稍肿，皮层及木质部变褐腐朽。防治方法包括农业防治和化学防治。\n\n7. **花腐病**：主要危害花朵、果实、叶片和枝梢，表现为花瓣变颜色，果实腐烂，叶片出现病斑。防治方法包括农业防治和化学防治。\n\n8. **立枯病**：主要危害樱桃砧木苗及多种果树砧木苗，表现为幼苗茎基部产生椭圆形暗褐色病斑，病苗倒伏死亡。防治方法包括农业防治和化学防治。\n\n9. **皱叶病**：属类病毒病，表现为叶片形状不规则，叶缘深裂，叶脉排列不规则，叶片皱缩。防治方法包括避免使用染毒的砧木和接穗，建立无病毒繁育圃等。\n\n10. **木腐病**：主要危害枝干心材，使木质腐朽，成轮纹状。防治方法包括采后施肥、合理轮作、果园管理、树体保护等。\n\n11. **病毒病**：表现为叶片变绿，形成深绿色舟形耳突，树势衰落。防治方法包括避免使用染毒的接穗、种子和花粉，建立无病毒繁育圃等。\n\n以上内容涵盖了樱桃树常见的病害及其防治方法，为樱桃树的种植和管理提供了参考。',
 # '以上内容是关于樱桃种植过程中可能遇到的主要病虫害及其防治方法的详细说明：\n\n### 病害\n1. **倍液或炭疽福美可湿性粉剂**：用于喷雾防治多种病害。\n2. **病毒病**：主要症状包括叶片碎裂、变绿、形成耳突等，传播途径包括带毒接穗、种子和花粉。\n3. **圆斑根腐病**：地上部症状包括萎蔫、青干、叶缘焦枯、枝枯等，传播途径为土壤中的镰刀菌。\n4. **小果病**：病果小、香味减少，传播途径包括嫁接、介壳虫等。\n5. **疮痂病**：果实和叶片出现暗褐色斑点，传播途径为樱桃黑星菌。\n6. **瘿瘤头蚜**：叶片背凹陷，形成泡状瘿，传播途径为卵在幼枝上越冬。\n7. **畸形果**：包括连体果、僵缩果、开裂果等，产生原因与遗传、营养、气候等因素有关。\n\n### 虫害\n1. **二斑叶螨**：以成螨和若螨刺吸嫩芽、叶片汁液，传播途径为越冬雌虫在土缝、枯枝等处越冬。\n2. **山楂叶螨**：以成、幼、若螨吸食芽、叶汁液，传播途径为受精成螨在枝干老翘皮下及根颈下越冬。\n3. **桑白蚧**：以雌成虫和若虫群集固定在枝条和树干上吸食汁液，传播途径为受精雌成虫在枝条上越冬。\n4. **卷叶蛾**：以幼虫吐丝缀连嫩叶和花蕾危害，传播途径为以小幼虫在翘皮缝、剪锯口等缝隙中越冬。\n5. **绿盲蝽**：以成虫和若虫刺吸嫩梢、嫩叶和幼果汁液，传播途径为卵在枝干伤口处越冬。\n6. **梨网蝽**：以成虫和若虫在叶背面吸食汁液，传播途径为以成虫在落叶、树干翘皮裂缝、杂草、土块缝隙中越冬。\n7. **黄尾刺蛾**：以幼虫危害叶片，传播途径为以结灰白色茧的3~4龄幼虫在树皮裂缝或枯叶里越冬。\n8. **天幕毛虫**：以幼虫群集在枝杈处吐丝结网危害叶片，传播途径为以完成胚胎发育的幼虫在卵壳中越冬。\n\n### 防治方法\n1. **农业防治**：清除枯枝落叶、杂草、病源等，改善果园环境。\n2. **化学防治**：根据病虫害发生规律和特点，选择合适的药剂进行防治。\n3. **生物防治**：利用天敌、微生物等生物因素进行病虫害防治。\n\n以上内容为樱桃种植过程中可能遇到的主要病虫害及其防治方法的总结。',
 # '以上内容是一份关于果树病虫害防治的详细说明，涵盖了多种果树害虫的简介、危害症状、发生规律和防治方法。以下是各部分内容的总结：\n\n1. **色泽比翅基和翅端部的为淡**：描述了某种害虫的色泽特征。\n\n2. **危害症状**：描述了害虫对果树的危害，如叶片残缺不全、叶片集中成片被害等。\n\n3. **发生规律**：介绍了害虫的繁殖周期、越冬方式、幼虫和成虫的活动习性等。\n\n4. **防治方法**：分为农业防治和化学防治，农业防治包括捕杀幼虫、利用天敌等；化学防治包括使用不同药剂进行喷洒。\n\n5. **具体害虫介绍**：包括：\n   - **黑星麦蛾**：主要危害樱桃、桃、李杏、苹果、梨等多种果树，幼虫危害嫩叶和嫩芽，成虫具有趋光性。\n   - **舟性毛虫**：主要危害樱桃、李、杏、苹果、梨等多种果树，幼虫取食叶片，成虫具有趋光性。\n   - **美国百蛾**：食性杂，主要危害林业树木，近年来在樱桃、梨等果园中经常发生，幼虫群集结网危害。\n   - **尺蠖**：主要危害苹果、梨、樱桃等多种果树，幼虫危害嫩枝、芽和叶，成虫具有趋光性。\n   - **天牛**：主要危害樱桃、桃、杏、李等果树，幼虫在树体的枝干内蛀食危害。\n   - **透翅蛾**：主要危害樱桃、桃、李、杏、苹果、梨等多种果树，幼虫食害树的主干和大枝的韧皮部。\n   - **梨小食心虫**：主要危害桃、楼桃、李、梨等果树嫩梢，幼虫危害嫩梢。\n   - **潜叶蛾**：主要危害桃、樱桃、李、苹果等果树，幼虫潜入叶片内取食叶肉。\n   - **刺蛾**：俗称洋辣子，主要危害樱桃、苹果、梨等多种果树，幼虫取食叶肉。\n   - **大叶青蝉**：又名跳蝉、大绿叶蝉，主要危害樱桃、桃、李、杏等多种果树，成虫和若虫吸食枝叶的汁液。\n   - **金龟子**：俗称瞎撞、金壳虫、金盖虫等，主要危害多种果树的花、叶片及果实。\n\n以上内容为果树病虫害防治的详细介绍，有助于果农了解各种害虫的特征和防治方法，从而有效保护果树生长。',
 # '以上内容主要涉及樱桃的病虫害防治、营养缺乏症状及其防治方法，以及樱桃的栽培管理措施。\n\n1. 樱桃病虫害防治：\n   - 主要病虫害包括金龟子、象甲、蛴螬等。\n   - 防治方法包括农业防治、化学防治和物理防治，如人工捕杀、使用杀虫剂、安装黑光灯诱杀等。\n\n2. 樱桃营养缺乏症状及其防治方法：\n   - 常见的营养缺乏症状包括缺镁、缺硼、缺铁、缺锌、缺钙等。\n   - 防治方法包括施用肥料、叶面喷施、土壤改良等。\n\n3. 樱桃栽培管理措施：\n   - 环境管理措施包括温室覆盖、升温、温度调控、湿度调控、光照调控、气体调控等。\n   - 通过合理的管理措施，保证樱桃树的生长发育和产量。\n\n4. 常用杀菌剂的配置：\n   - 波尔多液和石硫合剂是樱桃园中常用的杀菌剂，用于防治叶斑病、介壳虫、叶蜡等。\n   - 配置方法及注意事项在文中有所说明。\n\n总之，以上内容为樱桃种植者提供了病虫害防治、营养缺乏症状及防治方法、栽培管理措施等方面的知识，有助于提高樱桃的产量和品质。',
 # '以上内容主要介绍了樱桃在温室和大棚种植过程中的关键技术管理措施，涵盖了以下几个方面：\n\n1. **气体调控**：包括二氧化碳和有害气体的控制，以保证樱桃树光合作用和生长环境的健康。\n\n   - **二氧化碳**：通过通风换气、增施有机肥、人为补充二氧化碳等方法调节棚内二氧化碳浓度。\n   - **有害气体**：如氨气、二氧化氮、二氧化硫、一氧化碳、乙烯和氯等，通过合理施肥、控制施肥量、通风换气、使用安全无毒的塑料制品等措施减少有害气体的产生。\n\n2. **花果管理措施**：包括提高花蕾质量、疏花疏果、辅助授粉、提高坐果率、防落果裂果和促进花芽分化等。\n\n   - **提高花蕾质量**：通过增加光照、控制温度等措施。\n   - **疏花疏果**：合理疏除瘦小花芽和果实，提高果实品质。\n   - **辅助授粉**：通过蜜蜂授粉或人工授粉提高坐果率。\n   - **提高坐果率**：通过喷施叶面肥、除萌摘心等措施。\n   - **防落果裂果**：通过保持土壤水分、降低空气湿度等措施。\n   - **促进花芽分化**：通过叶面补肥等措施。\n\n3. **土壤以及水肥管理措施**：包括土壤管理、施肥管理和灌水管理。\n\n   - **土壤管理**：包括翻土、覆盖地膜、覆草、覆盖园艺地布等。\n   - **施肥管理**：包括设施樱桃需肥特点、施肥依据、施肥原则、施肥措施和施肥方法等。\n   - **灌水管理**：包括灌水时间、灌水方法和灌水原则等。\n\n4. **整形修剪措施**：包括树体类型、与修剪相关的特性等。\n\n   - **树体类型**：分为乔化型和矮化型两种。\n   - **与修剪相关的特性**：包括树冠与根系特性、芽的异质性、顶端优势等。\n\n以上内容旨在指导樱桃在温室和大棚种植过程中的管理，以提高产量和果实品质。',
 # '以上内容主要介绍了樱桃树的整形修剪技术，涵盖了从树体结构、修剪原则、修剪时期、主要修剪方法到不同树形和结果枝组的修剪等多个方面。\n\n**主要内容总结如下**：\n\n**1. 树体结构**：\n- 树体由地下根系和地上树冠组成。\n- 树冠包括主干、中心干、主枝、侧枝、辅养枝、延长枝、竞争枝、徒长枝、结果枝和结果枝组等。\n\n**2. 修剪原则**：\n- 根据品种特性、树体发育时期和树势确定修剪方法和程度。\n- 建造合理的树体骨架，主从分明，条理清楚。\n- 轻剪为主，轻重结合，长期壮树、高产优质。\n- 开张角度，促进成花，消除竞争枝，促进花芽形成。\n\n**3. 修剪时期**：\n- 生长期：从萌芽至树体停长落叶前，最适宜时间为萌芽至夏末。\n- 休眠期：从落叶后到萌芽前，最适宜时间为升温后至萌芽初。\n\n**4. 主要修剪方法**：\n- 拉枝、缓放、短截、疏枝、回缩、摘心、拿枝、刻芽、抹芽等。\n\n**5. 主要树形**：\n- 主干疏层形、自由纺锤形、小冠疏层形、KGB形、自然开心形。\n\n**6. 结果枝组的修剪**：\n- 结果枝组的培养：单轴延伸式、多式。\n- 结果枝组的配置：根据树冠位置、主枝位置、角度和层间距进行配置。\n- 结果枝组的修剪：根据生长势进行短截、回缩等。\n\n**7. 结果期果树的修剪**：\n- 初结果期：完善树形，增加枝量，培养结果枝组，平衡树势。\n- 盛果期：保持树势健壮，促使结果枝和结果枝组保持较强的结果能力，延长经济寿命。\n- 衰老期：采取回缩更新促壮措施，保持树体长势中庸。',
 # '以上内容主要涉及樱桃的栽培技术，包括以下几个方面：\n\n1. **樱桃树的修剪**：根据树龄、树势和结果枝组的长势，采取不同的修剪措施，如回缩更新、培养新结果枝组等。不同品种的樱桃修剪方法也有所不同。\n\n2. **衰老期樱桃树的修剪**：衰老期樱桃树应采取回缩措施，并利用潜伏芽培养新的主枝或结果枝。\n\n3. **不同品种樱桃树的修剪**：根据不同品种的樱桃特性，采取不同的修剪方法，如红灯、美早等直立生长的品种宜轻剪缓放，而横生生长的品种宜适当短截。\n\n4. **移栽树的修剪**：移栽树应适度修剪，保证树体缓势快、生长快，并注意疏除竞争枝和徒长枝。\n\n5. **常见问题**：包括树形紊乱、树冠过高或过低、短截过重、轻剪缓放过重、剪口距离、角度等不合理等。\n\n6. **采收时期及方法**：根据果实成熟度和销售需求确定采收时期，并进行分级包装。\n\n7. **采后树体管理**：采收后进行放风锻炼、保护叶片、施肥浇水等管理措施。\n\n8. **设施主栽品种及其特性**：介绍了福晨、甘露、早红珠、状元红、红灯、早露、明珠、福星、佳红、先锋、俄罗斯8号等樱桃品种的特性和栽培要点。\n\n总之，以上内容为樱桃的栽培提供了全面的指导，包括修剪、采收、管理等方面，有助于提高樱桃的产量和品质。',
 # '以上内容主要介绍了多种樱桃品种的特性、栽培技术、常见问题及解决方法。\n\n**主要内容总结如下**：\n\n**一、樱桃品种及特性**\n\n1. **俄罗斯8号**：中庸早果型品种，树势中庸，结果早，成花量大。\n2. **红南阳**：日本选育的极晚熟品种，果个大，肉质硬，甜味大。\n3. **美早**：美国品种，果大、质优、肉硬、耐贮运、早丰产。\n4. **美国1号**：美国原产，果形较大，呈心脏形，果肉肥厚多汁。\n5. **萨米脱**：加拿大品种，中熟、大果型、红色、异花授粉优良品种。\n6. **晓文一号**：果实肾脏形，果肉黄色，风味浓香，品质优。\n7. **布鲁克斯**：美国加州大学育成，早熟、红色、脆甜型、异花授粉优良品种。\n8. **拉宾斯**：加拿大品种，果实大而颜色红艳，营养价值丰富。\n9. **绣珠**：中熟型，果实大，果肉黄色，风味酸甜可口。\n10. **大将锦**：果肉硬，外观漂亮，糖度在20度以上，多汁，口味良好。\n11. **金顶红**：适应性很强，丰产性品种，果实色泽亮丽，裂果较少。\n12. **艳阳**：加拿大品种，果实大型，平均单果重13克左右，圆形。\n13. **雷尼**：美国华盛顿州育成，黄色中熟品种，果大，风味好。\n14. **饴珠**：果实宽心脏形，肉质较脆，肥厚多汁，风味酸甜适口。\n15. **晚红珠**：果实宽心脏形，整齐，果皮全而鲜红色，有光泽。\n16. **彩虹**：中晚熟甜樱桃新品种，果实大，平均单果质量7.7克。\n17. **香泉1号**：果实大，果皮黄色带红晕，果肉黄色，硬、多汁，酸甜可口。\n18. **春绣**：果实心脏形，果肉红色，肉质细脆，硬肉型，耐贮运。\n\n**二、樱桃栽培技术**\n\n1. **栽植时期**：分为春栽和秋栽两个时期。\n2. **施肥**：分为春夏季、采收后和秋季施肥三个阶段。\n3. **灌水**：灌水应防止过频过量，雨季积水应及时排出。\n4. **整形修剪**：主要有自然丛状形、自然开心形、主干疏层形等几种形式。\n\n**三、樱桃常见问题及解决方法**\n\n1. **落花落果**：原因有花芽饱满程度差、萌芽和开花期温度过高、空气过于干燥等，解决方法有促进花芽饱满、严格掌握浇水时期和浇水量等。\n2. **花芽变少**：原因有对樱桃的花芽分化时期的认识有误、负载量大等，解决方法有掌握花芽分化的关键时期、合理负载等。\n3. **枝干光秃和枯枝死树**：原因有升温前过早修剪、高浓度的PBO、多效唑植物生长调节剂类药剂多年连续在生育期使用等，解决方法有改休眠期修剪为萌芽期修剪、不超标施用植物生长调节剂等。\n4. **二次开花**：原因有叶片受害严重、采后修剪过重、树体无生长量的情况下高温干旱等，解决方法有采收前完成生长期的整形修剪工作、采收后尽量不修剪等。\n5. **肥料危害**：原因有土壤施肥和叶面喷肥两种，解决方法有防止肥料距根系太近、施肥过量等。',
 # '这份文档详细介绍了设施樱桃栽培的多个方面，包括田间管理、设施建设以及环境因素对樱桃生长的影响。以下是内容的总结：\n\n### 田间管理\n\n1. **肥害预防**：避免过量施肥，特别是有机肥需发酵处理，化肥需挖沟施入并与土壤混合。\n2. **叶面喷肥**：注意稀释比例，避免滥用增效剂和坐果剂。\n3. **药物危害**：避免浓度过高，正确使用，并注意药剂混合可能引起的化学反应。\n4. **高温危害**：保持适宜的温湿度，避免高温和干燥对花器官和授粉的影响。\n5. **冷水危害**：使用地下水或预热水灌溉，避免冷水对根系的影响。\n6. **涝害**：改善排水系统，避免土壤积水。\n7. **雪灾与冻害**：加强温室和大棚的防雪和保温措施。\n8. **天气变化剧烈危害**：适时遮阴，避免强光对叶片的伤害。\n9. **风害**：加强温室和大棚的固定和抗风能力。\n\n### 设施樱桃田间管理手册\n\n1. **休眠期**：控制温湿度，清除枯叶。\n2. **萌芽期**：解除休眠，修剪，喷药，施肥，浇水，翻树盘，拉枝，喷花前水，防病虫害。\n3. **开花期**：调控温度和湿度，辅助授粉，清除花瓣。\n4. **果实发育期**：调控温度和湿度，防治病虫害，整形修剪，施肥，浇水。\n5. **采收期**：采收方法，浇水。\n6. **放风锻炼期**：放风锻炼，浇水施肥。\n7. **露地生长期**：适时浇水排涝，病虫害防治，施基肥，修剪，覆盖。\n\n### 设施园区建设\n\n1. **设施建设基本要求**：可靠性、耐久性、内部空间、节能、标准化和装配化。\n2. **地址选择**：环境条件、土壤条件、灌溉条件。\n3. **设施类型**：促成栽培、防鸟害栽培、防雨和防霜雹栽培。\n4. **设施性能简介**：光照、温度、湿度。\n5. **设施建造**：温室设计（方位、长度、宽度、矢高、前后屋面角等），墙体，后屋面。\n\n这份文档为设施樱桃栽培提供了全面的技术指导。',
 # '以上内容主要涉及温室和大棚的设计、建造及附属设施设备，以下是对内容的总结：\n\n1. **温室和大棚设计**：\n   - 温室后屋面一般较短，以扩大采光面，但北纬40°以北地区不宜太短，后屋面水平投影宽度应不少于1.5米。\n   - 墙体材料多样，厚度因气候条件而异，寒冷地区可使用窑洞式墙体。\n   - 温室间距需考虑冬至前后不遮光，一般前后排温室间距为温室矢高的1.8~2.5倍，左右并排温室间隔一般为4~6米。\n\n2. **温室建造**：\n   - 常用结构为半拱圆式钢架结构温室，包括无柱有墙体温室和有柱无墙体温室。\n   - 无柱有墙体温室结构包括半圆拱形前屋面、墙体、后墙顶梁、地梁等。\n   - 有柱无墙体温室结构与无墙体温室类似，但后墙和两侧山墙用钢骨架代替。\n\n3. **大棚设计**：\n   - 方位：南北向延长建造，光照分布均匀。\n   - 跨度：一般为8~20米。\n   - 长度：一般为50~100米。\n   - 高度：单栋大棚以2.5~4米为宜，连栋钢架大棚可达3.5~4.5米。\n   - 通风：采用2道扒缝通风或安装自动或半自动通风装置。\n\n4. **大棚建造**：\n   - 常见类型：单栋和连栋大棚，连栋大棚分为有覆盖和无覆盖两种类型。\n   - 单栋大棚：跨度15~20米，高4~4.5米，拱架与拉筋的建造与温室相同。\n   - 连栋大棚：骨架采用圆钢拱型悬梁结构，棚顶用圆钢焊接成拱形吊梁。\n\n5. **设施覆盖物**：\n   - 塑料薄膜：聚乙烯长寿无滴膜、聚乙烯无滴防雾膜和聚烯烃膜等。\n   - 外保温材料：草帘、保温被等。\n   - 内保温材料：内保温被。\n\n6. **附属设施设备**：\n   - 卷帘机：电动卷帘机，有卷杠式、单臂式和爬坡式。\n   - 卷帘机遥控设备：遥控器。\n   - 输电线路：用于卷放草帘、灌溉和照明设备等。\n   - 灌溉设施：冬季灌溉用水为深井水，保持8℃以上的水温。\n   - 作业房：管理人员休息或放置工具等场所。\n   - 温湿度监控设备：水银温度计、酒精温度计、干湿球温度计、电子温湿度计等。\n   - 卷帘和固膜绳：尼龙绳。',
 # '以上内容主要介绍了番茄的生物学特征、生长发育周期以及对环境条件的要求，以及番茄的主要优良品种。\n\n**一、番茄生物学特征**\n\n1. **根系**：番茄根系发达，主根和侧根均强，根系深度和广度受土壤、施肥等因素影响。\n2. **茎**：番茄茎为半直立茎，分枝力强，具有顶端优势。根据生长习性，可分为有限生长型和无限生长型。\n3. **叶**：番茄叶为不整齐奇数羽状复叶，叶形、叶色和叶序是区分品种的重要特征。\n4. **花**：番茄花为完全花，自花授粉，花色为黄色。花芽分化过程中易出现带化现象，形成畸形果。\n5. **果实**：番茄果实为多汁浆果，形状、大小、颜色、心室数和风味等因品种不同而异。\n6. **种子**：番茄种子呈扁平短卵形或心脏形，发芽力强，寿命较长。\n\n**二、番茄生长发育周期**\n\n番茄一生经历发芽期、幼苗期、开花期和结果期。开花期和结果期没有明确界限，但栽培上通常将开花期视为营养生长盛期，结果期视为生殖生长盛期。\n\n**三、番茄生长发育对环境条件的要求**\n\n番茄喜温、喜光、怕霜、怕热、耐肥、半耐旱。影响番茄生长发育的因素包括温度、光照、水分、土壤及养分、气体等。\n\n**四、番茄主要优良品种**\n\n番茄品种繁多，根据生长习性可分为有限生长型和无限生长型。不同品种的形态特征和生长习性差异较大。',
 # '以上内容主要介绍了番茄的品种类型、分类方法以及一些主要优良品种的介绍。\n\n**1. 番茄品种类型及分类方法**\n\n* **依生长习性分类**：有限生长型和无限生长型。\n* **依栽培用途分类**：普通鲜食类、加工番茄类、樱桃番茄类。\n* **按果实颜色分类**：大红色、粉红色、金黄色等。\n* **按果实形状分类**：扁平形、圆形、长圆形等。\n* **按果实大小分类**：特大果、大果、中果、小果、特小果。\n* **按熟性分类**：最早熟、次早熟、早熟、中熟、晚熟。\n\n**2. 主要优良品种介绍**\n\n文中详细介绍了多种番茄优良品种，包括：\n\n* **易农1号、欧斯特2号、甜番贝、番之味3号、番之味5号、甜脆脆、台南喜贝、好柿来、宝德冬瑞、塔丽卡、番之味8号、金宝樱桃番茄、优拉52、优拉119、优拉121、春喜一号、春喜二号、春喜三号、粉尊八号、粉尊九号、苏红2003号、江蔬14号、江蔬1号、江蔬3号、浙杂809、浙粉202、浙粉701、浙杂501、皖粉5号、皖粉208、金棚1号、东农709、亚洲红冠、合作906、中杂106、FA-189、瑞德莱特、苏粉8号、苏粉9号、苏粉10号、苏红9号、TY209、苏粉12号、浙杂301、浙杂204、浙杂806、浙杂203、浙杂205、中杂9号、中杂12号、中杂11号、中杂101、合作908等。\n\n这些品种具有不同的生长习性、果实性状、抗病性、适应性等特点，适用于不同的栽培方式和地区。',
 # '这份文档主要介绍了多种番茄品种的特性和应用，以及番茄的育苗技术。\n\n**番茄品种介绍**：\n\n- 文档列举了多种番茄品种，包括中杂101、合作908、合作918、合作919、申粉918、渝粉109、金棚M6、晋番茄6号、仙客1号、仙客5号、仙客6号、东农711、莎龙、华番2号、华番3号、FA-1420、格瑞斯、欧盾、欧冠、齐达利、迪芬尼等。\n- 这些品种涵盖了不同的生长习性、果形、颜色、抗病性、产量和适应性，适用于不同的栽培环境和用途。\n\n**番茄育苗技术**：\n\n- 文档介绍了多种育苗方式，包括遮阳棚育苗、冷床育苗、电热温床育苗和穴盘育苗。\n- 每种育苗方式的特点、技术要点和管理方法都有详细的说明。\n\n**品种选用**：\n\n- 文档根据栽培目的、茬口、自然条件和栽培形式等因素，介绍了如何选择合适的番茄品种。\n\n**总结**：\n\n这份文档为番茄种植者提供了丰富的信息和指导，帮助他们选择合适的品种和育苗技术，提高番茄产量和品质。',
 # '以上内容主要介绍了番茄穴盘育苗和嫁接育苗的技术和方法，包括以下几个方面：\n\n1. 穴盘育苗：\n   - 穴盘选择：根据苗龄选择不同孔数的穴盘。\n   - 基质准备：配制草炭和蛭石混合基质，加入复合肥和鸡粪。\n   - 播期确定：根据定植期确定播种期。\n   - 播种：采用机械化或人工播种，注意播种数量和安全系数。\n   - 苗期管理：包括催芽、温度、湿度、光照、水分和病虫害防治等。\n   - 成苗标准：根据穴盘孔穴大小确定商品苗标准。\n\n2. 嫁接育苗：\n   - 砧木选择：选择抗病性强、根系强大、耐热、对土壤适应性强或抗根结线虫的品种。\n   - 接穗选择：选择品质优、坐果率高且丰产的优良品种。\n   - 嫁接方法：包括劈接法、靠接法、插接法、针接法和套管法等。\n   - 嫁接后的管理：包括温度、湿度、光照、水分和病虫害防治等。\n\n3. 育苗前的准备：\n   - 苗床准备：选择地势高燥、光照充足、排灌方便、土质肥沃、富含腐殖质、易于通风管理及近两年未种过茄果类的地块。\n   - 床土准备：配制床土，包括田土、腐熟过筛有机肥和化肥等。\n   - 种子处理：包括晒种、浸种及消毒、干热处理、低温和变温处理、种子包衣和催芽等。\n\n4. 播种：\n   - 采用干籽直播或浸种催芽播种。\n   - 覆盖细土，保持适宜的水分和温度。\n\n5. 苗期管理：\n   - 播种至分苗阶段的管理：维持较高的温度，保持适宜的水分和光照。\n   - 分苗至定植前的管理：分苗、温度管理、光照管理、水分管理、病虫害防治等。\n\n以上内容为番茄育苗的全面介绍，涵盖了育苗前的准备、播种、苗期管理、嫁接育苗等方面，为番茄种植者提供了实用的技术指导。',
 # '这份文档详细介绍了番茄的育苗、定植和田间管理技术，以下是内容的总结：\n\n### 育苗管理\n- **温度管理**：白天温度超过35°C时通风降温，温度下降后停止通风。保持白天20~25°C，夜间15~20°C。\n- **光照管理**：通过早揭晚盖延长光照时间，阴雨天气增加光照。\n- **湿度管理**：保持床土干湿适中，根据需要浇水，避免湿度过大。\n- **追肥**：根据幼苗生长情况施用速效肥，如尿素、磷酸二氢钾等。\n- **常见问题及解决办法**：包括土面板结、出苗不整齐、幼苗顶壳出土、徒长苗、僵化苗、风干、沤根、烧苗、寒根、闪苗、风溜苗和烧苗等。\n\n### 定植\n- **定植前的准备工作**：轮作倒茬，深耕冻堡晒堡，施足基肥，整地起垄。\n- **定植技术**：适龄壮苗，合理定植密度，选择无风晴天进行。\n\n### 田间管理\n- **施肥与浇水**：根据植株生长阶段合理施肥，保持土壤湿润。\n- **搭架与绑蔓**：搭架绑蔓，改善植株生长环境。\n- **整枝打杈与摘心**：合理整枝，控制植株生长，促进果实发育。\n- **防止落花落果**：分析落花落果的原因，采取相应措施。\n\n以上内容为番茄种植过程中各个阶段的管理要点，旨在提高番茄的产量和品质。',
 # '以上内容主要介绍了番茄的栽培技术，包括以下几个部分：\n\n1. **番茄栽培管理**：\n   - **适时定植**：选择适宜的定植时间，尽量带土坨，减少根系损失。\n   - **肥水管理**：保持土壤湿润，做好防寒保温，适时通风降温降湿。\n   - **整枝打杈**：合理调节植株营养生长和生殖生长的关系，防止徒长。\n   - **病虫害防治**：防治病虫危害和机械损伤。\n\n2. **使用植物生长激素**：\n   - **激素作用**：刺激植物器官的新陈代谢，促进果实发育，提高坐果率。\n   - **常用激素**：防落素（番茄灵）和2,4-D。\n   - **使用方法**：涂抹法、蘸花法、喷雾法。\n   - **注意事项**：浓度不能过高，避免药害，不宜重复处理。\n\n3. **番茄采收与催熟**：\n   - **适时采收**：根据果实成熟期和目的选择合适的采收时间。\n   - **催熟方法**：加温处理、乙烯利催熟。\n\n4. **番茄主要栽培类型及栽培技术**：\n   - **春季大棚早春栽培**：选择早熟、抗病、耐贮运的品种，培育壮苗，加强肥水管理，做好植株调整和病虫害防治。\n   - **秋延后大棚栽培**：选择早熟、抗病、耐热、耐贮运的品种，注意播种期和苗期管理，做好定植、肥水管理、保温防寒、植株调整和病虫害防治。\n   - **冬春日光温室栽培**：选择耐低温、耐弱光、不易徒长的中熟或中晚熟品种，注意播种期、苗期管理、整地定植、肥水管理、保温防寒、植株调整和病虫害防治。\n\n以上内容涵盖了番茄栽培的各个环节，为种植者提供了详细的指导。',
 # '这份文档详细介绍了番茄在日光温室中的不同栽培方式和管理技术，包括：\n\n1. **播种与育苗**：介绍了播种时间、苗床选择、播种方法、间苗、分苗等步骤，以及苗期管理和病虫害防治。\n\n2. **整地与定植**：包括施基肥、消毒、整地作畦、铺设地膜等步骤，以及定植时间、密度、方法等。\n\n3. **定植后管理**：\n   - **保花保果**：介绍了使用植物生长调节剂促进果实膨大和防止落花落果的方法。\n   - **增温保温**：介绍了日光温室的增温保温措施，如密封性能、防寒沟、草苫等。\n   - **增强光照**：介绍了增加光照的方法，如选择透光率高的塑料薄膜、张挂反光幕等。\n   - **肥水管理**：介绍了浇水、施肥的时间和方法，以及二氧化碳施肥等。\n   - **病害防治**：介绍了番茄常见病害和虫害的防治方法。\n   - **采收**：介绍了番茄的成熟期和采收标准。\n\n4. **秋冬日光温室栽培**：介绍了秋冬番茄的品种选择、育苗、整地定植、定植后管理等技术。\n\n5. **长季节日光温室栽培**：介绍了长季节番茄的品种选择、育苗、整地定植、定植后管理等技术。\n\n6. **番茄主要病虫害及其防治技术**：介绍了番茄的生理性病害和常见病虫害的症状、发病原因和防治方法。\n\n以上内容为番茄日光温室栽培提供了全面的指导。',
 # '以上内容主要介绍了番茄在种植过程中可能遇到的各种病害及其防治方法，包括非侵染性病害和侵染性病害。\n\n**非侵染性病害**：\n1. **畸形果**：由于低温、高湿、多氮等环境因素导致幼苗徒长，或水肥失调、激素使用不当等引起的果实形态异常。\n2. **卷叶病**：叶片卷曲、皱缩，影响光合作用，可能由摘心和整枝过早、氮肥过多、缺磷、缺钾、病毒病等引起。\n3. **裂果**：果实开裂，影响外观和运输，可能由高温、强光、干旱、缺钙等引起。\n4. **空洞果**：果皮凹陷，果肉少，可能由品种选择不当、激素使用不当、光照不足、管理不当等引起。\n5. **脐腐病**：果实脐部形成暗绿色水渍状病斑，可能由水分供应不均、缺钙、土壤肥料浓度过大等引起。\n6. **日灼病**：果实或叶片被太阳光灼伤，影响品质，可能由高温、干旱、光照不足等引起。\n7. **缺素症**：由于缺乏氮、钾、磷、镁、硼、钙等营养元素引起的症状。\n\n**侵染性病害**：\n1. **青枯病**：细菌性枯萎病，由青枯假单胞杆菌引起，高温高湿有利于发病。\n2. **早疫病**：真菌性病害，由茄链格孢菌引起，高温高湿有利于发病。\n3. **晚疫病**：真菌性病害，由致病疫霉引起，多雨、低温有利于发病。\n\n**防治方法**：\n1. **选用抗病品种**。\n2. **加强栽培管理**：合理施肥、浇水、整枝、摘心等。\n3. **药剂防治**：根据病情选择合适的农药进行防治。\n4. **其他措施**：如轮作、土壤消毒、种子处理等。\n\n通过以上措施，可以有效预防和控制番茄病害的发生，提高番茄产量和品质。',
 # '以上内容详细介绍了番茄在种植过程中可能遇到的主要病害及其防治方法，主要包括以下几种病害：\n\n1. **番茄晚疫病**：由真菌引起，通过风雨传播，适宜温度18-20°C，高湿度95%以上。防治方法包括选用抗病品种、加强田间管理等。\n\n2. **灰霉病**：由真菌引起，主要危害果实，适宜温度21-23°C，高湿度90%以上。防治方法包括选用抗病品种、加强栽培管理等。\n\n3. **叶霉病**：由真菌引起，主要危害叶片，适宜温度20-25°C，高湿度90%以上。防治方法包括选用抗病品种、种子处理、加强栽培管理等。\n\n4. **病毒病**：由病毒引起，包括花叶型、条斑型和蕨叶型，主要通过接触和蚜虫传播。防治方法包括选用抗病品种、种子处理、加强田间管理等。\n\n5. **番茄黄化曲叶病毒病**：由病毒引起，主要通过烟粉虱传播。防治方法包括强化虫情调查、选择抗病品种、控制虫源等。\n\n6. **根结线虫病**：由线虫引起，主要危害根部，适宜温度25-30°C。防治方法包括选用高抗品种、合理轮作、高温灭虫等。\n\n7. **斑枯病**：由真菌引起，主要危害叶片，适宜温度20-25°C。防治方法包括选用抗病品种、加强栽培管理等。\n\n这些病害的防治方法主要包括选用抗病品种、种子处理、加强栽培管理、药剂防治等。通过这些措施可以有效预防和控制番茄病害的发生。',
 # '以上内容详细介绍了番茄在种植过程中可能遇到的多种病害及其防治方法，以下是对这些内容的总结：\n\n### 番茄常见病害及其症状：\n\n1. **斑枯病**：叶片出现水渍状小圆斑，后形成圆形病斑，边缘深褐色，中部灰白色，严重时叶片枯死。\n2. **茎基腐病**：茎基部变褐，缢缩，叶片萎蔫变黄，最终整株枯死。\n3. **立枯病**：幼苗茎基部产生褐色病斑，绕茎发展，病部缢缩，地上部萎蔫枯死。\n4. **猝倒病**：幼苗茎基部呈水浸状病斑，绕茎一周，病部组织腐烂，幼苗倒伏死亡。\n5. **枯萎病**：茎一侧出现凹陷区，叶片发黄变褐后枯死，根部变褐。\n6. **菌核病**：叶片、果实、茎等部位出现灰褐色病斑，蔓延速度快，形成白色菌核。\n7. **绵疫病**：果实、叶片出现水浸状病斑，迅速扩展，皮下果肉变褐，密生白色霉层。\n8. **炭疽病**：果实出现水渍状透明小斑点，扩大后呈黑色，有同心轮纹，其上密生小黑点。\n9. **疮痂病**：叶片、茎、花、果实和果柄出现暗绿色小圆点斑，扩大后呈暗褐色圆形或近圆形，表面粗糙不平。\n10. **软腐病**：果实和茎部腐烂，具恶臭，茎部病斑初为青灰色，后呈灰褐色长条斑。\n11. **疫霉根腐病**：茎基部或根部产生水渍状病斑，地上部萎蔫，植株枯萎死亡。\n\n### 病害发生规律及条件：\n\n- 多数病害由真菌或细菌引起，以菌丝体、菌核、卵孢子等在土壤或病残体中越冬。\n- 高温高湿、土壤黏重、通风不良、肥料不足、连作等条件有利于病害发生。\n\n### 防治方法：\n\n1. **选用抗病品种**。\n2. **合理轮作**。\n3. **种子处理**。\n4. **加强田间管理**：包括合理施肥、灌溉、整枝、摘心等。\n5. **药剂防治**：根据病害种类选择合适的药剂进行喷洒或灌根。\n6. **清除病残体**：及时清除病残体，减少病原基数。\n\n通过以上措施，可以有效预防和控制番茄病害的发生，提高番茄产量和品质。',
 # '以上内容主要涉及番茄的病虫害防治，包括病害和虫害两大类。\n\n**病害**：\n\n1. **番茄疫霉根腐病**：由寄生疫霉和辣椒疫霉引起，通过雨水或灌溉水传播。防治方法包括选用抗病品种、加强田间管理、合理灌溉、使用药剂防治等。\n2. **番茄黄萎病**：由大丽轮枝泡菌引起，通过土壤、肥料、杂草等传播。防治方法包括选用抗病品种、种子处理、加强田间管理、使用药剂防治等。\n\n**虫害**：\n\n1. **棉铃虫**：以幼虫蛀食蕾、花、果为主，也啃食嫩茎、叶和芽。防治方法包括农业防治、物理防治、生物防治、化学防治等。\n2. **烟青虫**：以幼虫蛀食蕾、花、果为主，也可转株转果危害。防治方法包括农业防治、物理防治、生物防治、化学防治等。\n3. **白粉虱**：以成虫和若虫吸食植物汁液，引起叶片褪绿、变黄、萎蔫，甚至全株死亡。防治方法包括农业防治、物理防治、生物防治、化学防治等。\n4. **小地老虎**：以咬食番茄嫩茎、子叶、嫩叶为主，造成缺苗。防治方法包括农业防治、物理防治、化学防治等。\n5. **斜纹夜蛾**：以幼虫食叶、蕾、花及果实为主，严重时全株叶片被吃光。防治方法包括农业防治、物理防治、化学防治等。\n6. **美洲斑潜蝇**：以幼虫潜入叶片的上表皮下和下表皮上的叶肉组织取食危害，形成不规则白蛇形蛀道。防治方法包括加强植物检疫、物理防治、农业防治等。\n\n总体来说，番茄病虫害防治需要综合运用多种方法，包括农业防治、物理防治、生物防治和化学防治等，以达到最佳防治效果。',
 # '以上内容主要介绍了几种常见蔬菜害虫的防治方法，包括：\n\n1. 美洲斑潜蝇：介绍了其形态特征、生活习性和防治方法，如加强植物检疫、物理防治、农业防治、生物防治和化学防治等。\n\n2. 蚜虫：介绍了其形态特征、生活习性和防治方法，如农业防治、物理防治、生物防治和化学防治等。\n\n3. 茶黄螨：介绍了其形态特征、生活习性和防治方法，如农业防治和药剂防治等。\n\n4. 蝼蛄：介绍了其形态特征、生活习性和防治方法，如利用趋光性诱杀、设置毒饵、施用毒土等。\n\n总体来说，以上内容针对不同害虫的特点，提出了相应的防治措施，旨在帮助农民有效地控制蔬菜害虫，保障蔬菜产量和品质。']

        summarys1,summarys2 = merge_summary(summarys1,summarys2)
        if os.path.exists(os.path.join(".cache",f"{name}_contents.pkl")) == False:
            text_spliter = CharacterTextSplitter(chunk_size=1024, chunk_overlap=300)  # 400   0:0-200  1:150-350 2:300-400
            split_docs = text_spliter.split_documents(documents)
            contents = [i.page_content for i in split_docs]
            with open(os.path.join(".cache",f"{name}_contents.pkl"), "wb") as f:
                pickle.dump(contents, f)
        else:
            with open(os.path.join(".cache",f"{name}_contents.pkl"), "rb") as f:
                contents = pickle.load(f)
        self.content1 = contents + summarys1
        self.content2 = [""]*len(contents) + summarys2

class MyEmbModel():
    def __init__(self,model_dir):
        self.model = SentenceTransformer(model_dir).to("cuda" if torch.cuda.is_available() else "cpu")


    def to_emb(self,sentence):
        if isinstance(sentence,str):
            sentence = [sentence]
        return self.model.encode(sentence)

def cover_name(name):
    return "_".join(lazy_pinyin(name))

class MyEmbDatabase():
    def __init__(self,emb_dir,document,name):
        global client
        self.name = cover_name(name)
        self.emb_model = emb_model

        if client.has_collection(self.name):
            client.drop_collection(self.name)

        if client.has_collection(self.name) == False:
            schema = CollectionSchema([
                FieldSchema("id", DataType.INT64, is_primary=True),
                FieldSchema("text1", DataType.VARCHAR, max_length=18196),
                FieldSchema("emb", DataType.FLOAT_VECTOR, dim=self.emb_model.model.get_sentence_embedding_dimension()),
                FieldSchema("text2", DataType.VARCHAR, max_length=18196)
            ])

            index_params = client.prepare_index_params()
            index_params.add_index(
                field_name="emb",
                metric_type="COSINE",
                index_type="",
                index_name="vector_index"
            )

            client.create_collection(collection_name=self.name, schema=schema)
            client.create_index(self.name, index_params)

            for idx,(content1,content2) in tqdm(enumerate(zip(document.content1,document.content2)),total=len(document.content1),desc=f"构建{name}向量库中") :
                emb = self.emb_model.to_emb(content1)[0]
                client.insert(self.name,{"id":idx,"text1":content1,"text2":content2,"emb":emb})

        client.load_collection(self.name)

        # if os.path.exists(os.path.join(".cache",f"{name}_faiss_index.pkl")) == False:
        #     index = faiss.IndexFlatL2(self.emb_model.model.get_sentence_embedding_dimension())
        #     embs = self.emb_model.to_emb(contents)
        #     index.add(embs)
        #
        #     with open(os.path.join(".cache",f"{name}_faiss_index.pkl"),"wb") as f:
        #         pickle.dump(index,f)
        # else:
        #     with open(os.path.join(".cache",f"{name}_faiss_index.pkl"),"rb") as f:
        #         index = pickle.load(f)
        # self.index = index
        # self.contents = contents


    def search(self,content,topn=3):
        global  client

        if isinstance(content,str):
            content = self.emb_model.to_emb(content)

        result = client.search(self.name,content,output_fields=["text1","text2"],limit=topn)
        _,_,t1,t2 = zip(*[ (d["id"],d["distance"],d["entity"]["text1"],d["entity"]["text2"]) for d in result[0] ])
        t1,t2 = list(t1),list(t2)
        for i in range(len(t1)):
            if len(t1[i]) < 50:
                t1[i] = t2[i]

        return [i.replace("\n\n","") for i in t1]


        # distances , idxs = self.index.search(content,topn) # mlivus
        #
        # results = [self.contents[i] for i in idxs[0]]
        # return results

class MyDataBase:
    def __init__(self,path,name=None):
        if name is None:
            name = path

        if os.path.exists(os.path.join(path,"txt")) == False:
            print("对应的知识库txt文件夹不存在")
            exit(-999)
        if os.path.exists(os.path.join(path,"prompt.xlsx")) == False:
            print("prompt模板不存在")
            exit(-998)
        if os.path.exists(".cache") == False:
            os.mkdir(".cache")

        self.prompt_data = pd.read_excel(os.path.join(path,"prompt.xlsx"))
        self.document = MyDocument(os.path.join(path,"txt"),name)
        self.emb_database = MyEmbDatabase("./bge-base-zh-v1.5", self.document,name)

    def search(self,text,topn=3):
        return self.emb_database.search(text,topn)

def load_database(dir_path="database_dir"):
    dirs = [name for name in os.listdir(dir_path) if os.path.isdir(f"{dir_path}/{name}")]

    database_list = []
    database_namelist = []

    for dir in dirs:
        database = MyDataBase(f"{dir_path}/{dir}",dir)

        database_list.append(database)
        database_namelist.append(dir)

    return database_list,database_namelist

def function1(name,input3,input2):
    global database_list, database_namelist
    database = database_list[database_namelist.index(name)]


    result1 = []
    result2 = []

    result1.append("内容解析中......")
    yield "\n".join(result1),"\n".join(result2)

    all_report = ""
    for p_n, group in database.prompt_data.groupby("段落"):
        result1.append(f"第{p_n}段内容生成中......")

        yield "\n".join(result1), "\n".join(result2)

        p_n_content = []
        for question in group["prompt"]:
            search_result = database.search(question, 3)

            # search_result = "\n".join(search_result)

            prompt = f"请根据已知内容简洁明了的回复用户的问题，已知内容如下：```{search_result}```,用户的问题是：{question}，如何已知内容无法回答用户的问题，请直接回复：不知道，无需输出其他内容"

            response = get_ans(prompt)
            result1.append("检索及回答内容:\n")
            for trunk in response:
                result1[-1] += trunk.choices[0].delta.content
                yield "\n".join(result1), "\n".join(result2)


            result1[-1] = result1[-1].replace("\n", "")
            p_n_content.append(result1[-1])

            result1.append("*"*30)
            yield "\n".join(result1), "\n".join(result2)

        prompt_report = f"你是一个大学教授，你需要根据相关内容，来撰写一段内容，生成的结果必须严格来自相关内容，语言必须严谨、符合事实，不能使用第一人称，相关内容如下：\n```\n{''.join(p_n_content)}\n```\n生成的结果为："

        result1.append("第一段报告内容:\n")
        result2.append("\t\t\t")
        yield "\n".join(result1), "\n".join(result2)

        response = get_ans(prompt_report)

        for trunk in response:
            result1[-1] += trunk.choices[0].delta.content
            result2[-1] += trunk.choices[0].delta.content

            result1[-1] = result1[-1].replace("\n", "")
            result2[-1] = result2[-1].replace("\n", "")
            yield "\n".join(result1), "\n".join(result2)


        all_report += result2[-1]
        all_report += "\n"

        result1.append("*"*30)
        yield "\n".join(result1), "\n".join(result2)


def function2(name, text):
    global database_list, database_namelist
    database = database_list[database_namelist.index(name)]

    result = ""  # 改为字符串存储

    search_result = database.search(text,3)
    ref = "\n".join([f"参考内容{i+1}:\n{content}" for i,content in enumerate(search_result)])
    prompt = f"请从多个参考内容中，选择一个最有效的参考信息，详细回复用户的问题。注意：你的回答中不要出现“根据提供的参考内容”等字样，你的答案都应该来自于参考内容，尽可能使用原文进行回答。\n参考内容如下：\n```\n{ref}\n```\n用户的问题：\n```{text}```\n尽可能详细的回答："

    response = get_ans(prompt)

    for trunk in response:
        t = trunk.choices[0].delta.content
        t = t.replace("~","-")
        result += t  # 直接追加到字符串
        yield result  # 每次返回完整内容


def get_type_name(files):

    content = []
    for file in files:
        try:
            with open(file.name,encoding="utf-8") as f:
                data = f.readlines(1)
                content.extend(aly.tfidf(data[0]))
        except:
            continue
    count = Counter(content)
    kw = count.most_common(2)

    return "".join([i[0] for i in kw])

def upload(files):
    global  database_list, database_namelist,input1

    check_txt = False
    check_prompt_xlsx = False

    for file in files:
        if check_txt and check_prompt_xlsx:
            break
        if file.name.endswith(".txt"):
            check_txt = True
        elif file.name.endswith("prompt.xlsx"):
            check_prompt_xlsx = True
    else:
        if check_txt == False:
            raise Exception("请上传包含txt文档的文件夹")
        if check_prompt_xlsx  == False:
            raise Exception("请上传包含prompt.xlsx的文件夹")

    type_name = get_type_name(files)
    save_path = os.path.join("database_dir", type_name)

    if os.path.exists(save_path) == False:
        os.mkdir(save_path)
        os.mkdir(os.path.join(save_path,"txt"))
    for file in files:
        if file.name.endswith(".txt"):
            shutil.copy(file.name,os.path.join(save_path,"txt"))
        elif file.name.endswith("prompt.xlsx"):
            shutil.copy(file.name, save_path)

    database = MyDataBase(save_path,type_name)
    database_list.append(database)
    database_namelist.append(type_name)
    input1.choices.append((type_name,type_name))

    return type_name,database.prompt_data

def database_change(name):
    global database_list, database_namelist

    return database_list[database_namelist.index(name)].prompt_data

if __name__ == "__main__":
    client = MilvusClient(uri="http://192.168.1.138:19530")

    emb_model = MyEmbModel("./bge-base-zh-v1.5")

    database_list, database_namelist = load_database()

    # ----------------------------- 界面控件 -----------------------------
    input1 = gr.Dropdown(choices=database_namelist,label="知识库选择",value=database_namelist[0])
    input2 = gr.DataFrame(database_list[0].prompt_data,height=400)
    input3 = gr.UploadButton(label="上传知识库",file_count="directory")

    input4 = gr.Dropdown(choices=database_namelist,label="知识库选择",value=database_namelist[0])

    output1 = gr.Textbox(label="报告生成过程", lines=11, max_lines=14)
    output2 = gr.Markdown(label="报告生成内容")


    # ----------------------------- 界面启动 -----------------------------

    # interface1 = gr.Interface(function1,[input1,input3,input2],[output1,output2],submit_btn="点击生成报告",clear_btn=gr.Button("clear",visible=False),allow_flagging="never")
    # interface2 = gr.Interface(function2,[input4,"text"],"text",allow_flagging="never")
    # 修改界面组件
    interface2 = gr.Interface(
        function2,
        [input4, "text"],
        [gr.Markdown()],  # 输出类型改为Markdown组件
        # ["text",gr.Markdown()],  # 输出类型改为Markdown组件
        allow_flagging="never"
    )

    # tab_interface = gr.TabbedInterface([interface1,interface2],["报告生成","知识库问答"],title="RAG报告生成和问答")
    tab_interface = gr.TabbedInterface([interface2],["知识库问答"],title="RAG问答")

    with tab_interface as tab_interface:
        input1.change(database_change,input1,input2)
        input3.upload(upload,input3,[input1,input2])
        tab_interface.launch(server_name="home.onehot-tech.com",server_port=43999,show_api=False,share=True)