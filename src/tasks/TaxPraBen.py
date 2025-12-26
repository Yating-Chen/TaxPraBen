import os
import re
import time
import evaluate
import numpy as np
from openai import OpenAI
from lm_eval.base import Task, rf
from lm_eval.metrics import mean, bleu, chrf, ter
from .utils import process_text
from .zhutils import process_zhtext
from seqeval.metrics import f1_score as entity_score
from sklearn.metrics import f1_score, matthews_corrcoef, mean_squared_error
from bart_score import BARTScorer


class Classification(Task):
    CALCULATE_MCC = True
    LOWER_CASE = True
    VERSION = 1
    EVAL_LAST_TURN = True

    def reformulate_turn_req(self, req, turn_request, turn):
        return req

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def construct_requests(self, doc, ctx):

        cont_request = rf.greedy_until(ctx, {"until": None})
        return cont_request

    def doc_to_decontamination_query(self, doc):
        return doc["text"]

    def doc_to_text(self, doc):

        return doc["query"]

    def doc_to_target(self, doc):

        return doc["answer"]

    def process_results(self, doc, results):
        gold: str = doc["choices"][doc["gold"]]
        if self.LOWER_CASE:
            gold = gold.lower()
        ini_result = results[0].strip()
        if self.LOWER_CASE:
            ini_result = ini_result.lower()

        result = None
        for choice in doc["choices"]:
            if self.LOWER_CASE:
                choice = choice.lower()
            if choice in ini_result:
                result = choice
                break
        if result is None:
            result = "missing"

        acc = 1.0 if gold == result else 0.0

        results = {
            "acc": acc,
            "missing": int(result == "missing"),
            "f1": (result, gold),
            "macro_f1": (result, gold),
        }

        if self.CALCULATE_MCC:
            results["mcc"] = (result, gold)

        return results

    def higher_is_better(self):
        metrics = {
            "acc": True,
            "f1": True,
            "macro_f1": True,
            "missing": False,
        }
        if self.CALCULATE_MCC:
            metrics["mcc"] = True
        return metrics

    def weighted_f1(self, items):
        preds, golds = zip(*items)
        labels = list(set(golds))
        preds = np.array(preds)
        golds = np.array(golds)
        f1 = f1_score(golds, preds, average="weighted", labels=labels)
        return f1

    def macro_f1(self, items):
        preds, golds = zip(*items)
        labels = list(set(golds))
        preds = np.array(preds)
        golds = np.array(golds)
        f1 = f1_score(golds, preds, average="macro", labels=labels)
        return f1

    def matthews_corrcoef(self, items):
        preds, golds = zip(*items)
        labels = {label: i for i, label in enumerate(list(set(golds)))}
        preds = [labels.get(pred, -1) for pred in preds]
        golds = [labels.get(gold, -1) for gold in golds]
        return matthews_corrcoef(golds, preds)

    def aggregation(self):
        metrics = {
            "acc": mean,
            "missing": mean,
            "f1": self.weighted_f1,
            "macro_f1": self.macro_f1,
        }
        if self.CALCULATE_MCC:
            metrics["mcc"] = self.matthews_corrcoef
        return metrics


class TaxSCQ(Classification):
    DATASET_PATH = "DATASET_PATH"


class TaxTopic(Classification):
    DATASET_PATH = "DATASET_PATH"


class ClauseIdentify(Task):
    CALCULATE_MCC = True
    LOWER_CASE = True
    VERSION = 1
    EVAL_LAST_TURN = True

    def reformulate_turn_req(self, req, turn_request, turn):
        return req

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def construct_requests(self, doc, ctx):

        cont_request = rf.greedy_until(ctx, {"until": None})
        return cont_request

    def doc_to_decontamination_query(self, doc):
        return doc["text"]

    def doc_to_text(self, doc):

        return doc["query"]

    def doc_to_target(self, doc):
        return doc["gold"][0]

    def process_results(self, doc, results):
        gold_list = doc["gold"]
        if self.LOWER_CASE:
            gold_list = [g.lower() for g in gold_list]

        ini_result = results[0].strip()
        if self.LOWER_CASE:
            ini_result = ini_result.lower()

        result = None
        for choice in doc["choices"]:
            comp_choice = choice.lower() if self.LOWER_CASE else choice
            if comp_choice in ini_result:
                result = comp_choice
                break
        if result is None:
            result = "missing"

        acc = 1.0 if result in gold_list else 0.0

        results = {
            "acc": acc,
            "missing": int(result == "missing"),
            "f1": (result, gold_list[0]),
            "macro_f1": (result, gold_list[0]),
        }

        if self.CALCULATE_MCC:
            results["mcc"] = (result, gold_list[0])

        return results

    def higher_is_better(self):
        metrics = {
            "acc": True,
            "f1": True,
            "macro_f1": True,
            "missing": False,
        }
        if self.CALCULATE_MCC:
            metrics["mcc"] = True
        return metrics

    def weighted_f1(self, items):
        preds, golds = zip(*items)
        labels = list(set(golds))
        preds = np.array(preds)
        golds = np.array(golds)
        f1 = f1_score(golds, preds, average="weighted", labels=labels)
        return f1

    def macro_f1(self, items):
        preds, golds = zip(*items)
        labels = list(set(golds))
        preds = np.array(preds)
        golds = np.array(golds)
        f1 = f1_score(golds, preds, average="macro", labels=labels)
        return f1

    def matthews_corrcoef(self, items):
        preds, golds = zip(*items)
        labels = {label: i for i, label in enumerate(list(set(golds)))}
        preds = [labels.get(pred, -1) for pred in preds]
        golds = [labels.get(gold, -1) for gold in golds]
        return matthews_corrcoef(golds, preds)

    def aggregation(self):
        metrics = {
            "acc": mean,
            "missing": mean,
            "f1": self.weighted_f1,
            "macro_f1": self.macro_f1,
        }
        if self.CALCULATE_MCC:
            metrics["mcc"] = self.matthews_corrcoef
        return metrics


class TaxCrime(ClauseIdentify):
    DATASET_PATH = "DATASET_PATH"


class AbstractiveSummarization(Task):
    VERSION = 1
    DATASET_NAME = None
    EVAL_LAST_TURN = True

    def reformulate_turn_req(self, req, turn_request, turn):
        return req

    def has_training_docs(self):
        return False

    def has_validation_docs(self):
        return False

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def doc_to_text(self, doc):
        return doc["query"]

    def doc_to_target(self, doc):
        return doc["answer"]

    def process_results(self, doc, results):
        return {
            "rouge1": (doc["answer"], results[0]),
            "rouge2": (doc["answer"], results[0]),
            "rougeL": (doc["answer"], results[0]),
            "bert_score_f1": (doc["answer"], results[0]),
            "bart_score": (doc["answer"], results[0]),
        }

    def higher_is_better(self):
        return {
            "rouge1": True,
            "rouge2": True,
            "rougeL": True,
            "bert_score_f1": True,
            "bart_score": True,
        }

    def construct_requests(self, doc, ctx):
        cont_request = rf.greedy_until(ctx, {"until": None})
        return cont_request

    def rouge_score(self, items):
        golds, preds = zip(*items)
        rouge = evaluate.load("src/metrics/rouge")
        results = rouge.compute(predictions=preds, references=golds)
        return results

    def rouge1(self, items):
        results = self.rouge_score(items)
        return results["rouge1"]

    def rouge2(self, items):
        results = self.rouge_score(items)
        return results["rouge2"]

    def rougeL(self, items):
        results = self.rouge_score(items)
        return results["rougeL"]

    def bert_score(self, items):
        if getattr(self, "_cache_bertscore", None) is None:
            golds, preds = zip(*items)
            bertscore = evaluate.load("src/metrics/bertscore")

            model_type = os.getenv("BERTSCORE_MODEL_TYPE", "hfl/chinese-xlnet-base")

            self._cache_bertscore = bertscore.compute(
                predictions=preds,
                references=golds,
                num_layers=5,
                lang="zh",
                model_type=model_type,
            )
            return self._cache_bertscore
        else:
            return self._cache_bertscore

    def bert_score_f1(self, items):
        res = self.bert_score(items)
        return sum(res["f1"]) / len(res["f1"])

    def bart_score(self, items):
        golds, preds = zip(*items)

        checkpoint = os.getenv("BART_SCORE_CHECKPOINT", "facebook/bart-large-cnn")
        pth_path = os.getenv("BART_SCORE_PTH", "")

        if getattr(self, "_cache_bart_scorer", None) is None:
            scorer = BARTScorer(device=os.getenv("BART_SCORE_DEVICE", "cuda"),
                                checkpoint=checkpoint)
            if pth_path:
                scorer.load(path=pth_path)
            self._cache_bart_scorer = scorer

        res = self._cache_bart_scorer.score(srcs=preds, tgts=golds, batch_size=8)
        return sum(res) / len(res)

    def aggregation(self):
        return {
            "rouge1": self.rouge1,
            "rouge2": self.rouge2,
            "rougeL": self.rougeL,
            "bert_score_f1": self.bert_score_f1,
            "bart_score": self.bart_score,
        }


class TaxBoard(AbstractiveSummarization):
    DATASET_PATH = "DATASET_PATH"


class TaxQA(AbstractiveSummarization):
    DATASET_PATH = "DATASET_PATH"


class TaxRecite(AbstractiveSummarization):
    DATASET_PATH = "DATASET_PATH"


class TaxSum(AbstractiveSummarization):
    DATASET_PATH = "DATASET_PATH"


class TaxOpinion(AbstractiveSummarization):
    DATASET_PATH = "DATASET_PATH"


class MatchAnswer(Task):
    VERSION = 1
    DATASET_NAME = None
    EVAL_LAST_TURN = True

    def reformulate_turn_req(self, req, turn_request, turn):
        return req

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def should_decontaminate(self):
        return True

    def doc_to_decontamination_query(self, doc):
        return doc["text"]

    def doc_to_text(self, doc):
        return doc["query"]

    def construct_requests(self, doc, ctx):
        cont_request = rf.greedy_until(ctx, {"until": None})
        return cont_request

    def doc_to_target(self, doc):
        return doc["answer"]

    def process_results(self, doc, results):
        gold = doc["answer"]

        match = re.findall(r'[ABCDE](?:\W*[ABCDE]){1,4}', results[0])

        pres = re.sub(r'[^A-Z]', '', match[0]) if match else 'null'

        acc = 1.0 if pres == gold else 0.0

        return {
            "acc": acc,
        }

    def higher_is_better(self):
        return {
            "acc": True,
        }

    def aggregation(self):
        return {
            "acc": mean,
        }


class TaxMCQ(MatchAnswer):
    DATASET_PATH = "DATASET_PATH"


class ComputeAnswer(Task):
    VERSION = 1
    DATASET_NAME = None
    EVAL_LAST_TURN = True

    def reformulate_turn_req(self, req, turn_request, turn):
        return req

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def should_decontaminate(self):
        return True

    def doc_to_decontamination_query(self, doc):
        return doc["text"]

    def doc_to_text(self, doc):
        return doc["query"]

    def construct_requests(self, doc, ctx):
        cont_request = rf.greedy_until(ctx, {"until": None})
        return cont_request

    def doc_to_target(self, doc):
        return doc["answer"]

    def process_results(self, doc, results):
        try:
            gold = float(doc["answer"])
            formatted_gold = "{:.2f}".format(gold)
        except ValueError:
            print("标准答案 (gold) 格式不正确，无法转换为浮点数")
            return {"acc": 0.0}

        client = OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        try:
            pres = round(float(results[0]), 2)
            formatted_pres = "{:.2f}".format(pres)
            acc = 1.0 if formatted_pres == formatted_gold else 0.0
            return {"acc": acc}

        except Exception as e:
            print(f"直接比较失败: {e}, 尝试通过GPT提取答案...")

            query = re.search(r'问题为：(.+)', doc['query']).group(1)

            print('query\n', query)
            print('logit\n', results[0])

            input = f"你将会收到[描述文本]，由一个<问题>和一个包含该问题的<答案段落>构成，你需要从段落中提取问题对应的答案，如果段落中没有包含问题的答案，则输出“未知”即可，不要自己回答，一定不需要有任何多余的解释。以下是一个例子：<问题>：'本月应该缴纳的增值税额为xx万元？' <答案段落>：'...本月应该缴纳的增值税额为10.00万元。' 提取出的答案为：'10.00万元' [描述文本]:  <问题>：{query}  <答案段落>：{results[0]} "

            print('input\n', input)

            while True:
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        max_tokens=500,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": input}
                        ]
                    )

                    answer = response.choices[0].message.content.strip()

                    print('GPT返回的答案\n', answer)

                    extracted_number = None

                    match_wan_yuan = re.search(r'([-+]?\d*\.?\d+)\s?(?=万元|元)', answer)

                    match_percent = re.search(r'(?<=百分之)\d*\.?\d+', answer)

                    if match_wan_yuan:
                        extracted_number = match_wan_yuan.group(1)
                    elif match_percent:
                        extracted_number = match_percent.group(0)
                    else:
                        print("未找到符合条件的数字")
                        formatted_pres = "未知"

                    if extracted_number is not None:
                        pres = float(extracted_number)
                        formatted_pres = "{:.2f}".format(pres)

                    print('提取并处理后的数字\n', formatted_pres)

                    acc = 1.0 if formatted_pres == formatted_gold else 0.0

                    return {"acc": acc}

                except Exception as e:
                    print(f"发生错误: {e}, 正在重新尝试...")
                    time.sleep(2)

    def higher_is_better(self):
        return {
            "acc": True,
        }

    def aggregation(self):
        return {
            "acc": mean,
        }


class TaxCalc(ComputeAnswer):
    DATASET_PATH = "DATASET_PATH"


class CaseAnalysis(Task):
    VERSION = 1
    DATASET_NAME = None
    EVAL_LAST_TURN = True

    def reformulate_turn_req(self, req, turn_request, turn):
        return req

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def should_decontaminate(self):
        return True

    def doc_to_decontamination_query(self, doc):
        return doc["text"]

    def doc_to_text(self, doc):
        return doc["query"]

    def doc_to_target(self, doc):
        return doc["answer"]

    def construct_requests(self, doc, ctx):
        return rf.greedy_until(ctx, {"until": None})

    def process_results(self, doc, results):
        raw_output = results[0]
        query = doc["query"]
        gold = json.loads(doc["answer"])

        match = re.search(r'\{[\s\S]*?\}', query)
        required_format = match.group(0) if match else None

        if not required_format:
            print("未能提取到格式定义")

        gpt_input = (
            f"请你从模型输出中提取填空答案，若某一字段没有找到答案，则该字段留空，不要凭空生成答案，并严格按照以下格式输出：{required_format}，除核心思路外，其余字段都只返回数值，不要有任何符号和单位。\n"
            f"模型输出如下：\n{raw_output}\n"
            f"请只返回一个合法 JSON 对象，不要任何额外解释。"
        )

        client = OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        parsed = {}
        for _ in range(5):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    max_tokens=1000,
                    messages=[
                        {"role": "system", "content": "你是一个精准的JSON抽取助手。"},
                        {"role": "user", "content": gpt_input}
                    ]
                )
                content = response.choices[0].message.content.strip()
                print(f"GPT返回内容：{content}")
                parsed = json.loads(content)

                if not isinstance(parsed, dict):
                    print(f"GPT返回的不是字典格式: {type(parsed)}")
                    continue

                break
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                print(f"原始内容: {content}")
                time.sleep(2)
            except Exception as e:
                print("GPT格式化失败，重试中...", e)
                time.sleep(2)
        else:
            print("所有GPT格式化尝试都失败，返回默认分数")
            return {
                "score": 0.0,
                "bert_score_f1": 0.0,
                "acc_avg": 0.0,
            }

        pred_idea = parsed.get("核心思路", "")
        gold_idea = gold.get("核心思路", "")

        pred_idea = str(pred_idea) if pred_idea is not None else ""
        gold_idea = str(gold_idea) if gold_idea is not None else ""

        if not pred_idea.strip() or not gold_idea.strip():
            print("空的核心思路，跳过BERTScore")
            bert_f1 = 0.0

        else:
            try:
                print("正在加载 BERTScore 模块")
                bertscore = evaluate.load("src/metrics/bertscore")

                print("开始计算 BERTScore")
                print("预测核心思路:", repr(pred_idea))
                print("参考核心思路:", repr(gold_idea))

                model_type = os.getenv("BERTSCORE_MODEL_TYPE", "hfl/chinese-xlnet-base")

                bert_res = bertscore.compute(
                    predictions=[pred_idea],
                    references=[gold_idea],
                    lang="zh",
                    num_layers=5,
                    model_type=model_type,
                )
                bert_f1 = bert_res["f1"][0]
            except Exception as e:
                print("BERTScore计算失败", str(e))
                bert_f1 = 0.0

        acc_list = []
        for k, gold_v in gold.items():
            if k == "核心思路":
                continue
            if k not in parsed:
                acc_list.append(0.0)
                continue

            try:
                gold_float = round(float(gold_v), 2)
                pred_float = round(float(parsed[k]), 2)
                acc = 1.0 if gold_float == pred_float else 0.0
                acc_list.append(acc)
            except Exception as e:
                print(f"字段 {k} 比较失败: {e}")
                acc_list.append(0.0)

        acc_avg = mean(acc_list) if acc_list else 0.0

        final_score = (bert_f1 + acc_avg) / 2

        return {
            "score": final_score,
            "bert_score_f1": bert_f1,
            "acc_avg": acc_avg,
        }

    def aggregation(self):
        return {
            "score": mean,
            "bert_score_f1": mean,
            "acc_avg": mean,
        }

    def higher_is_better(self):
        return {
            "score": True,
            "bert_score_f1": True,
            "acc_avg": True,
        }


class TaxPlan(CaseAnalysis):
    DATASET_PATH = "DATASET_PATH"


class CheckCase(Task):
    VERSION = 1
    DATASET_NAME = None
    EVAL_LAST_TURN = True

    def reformulate_turn_req(self, req, turn_request, turn):
        return req

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def should_decontaminate(self):
        return True

    def doc_to_decontamination_query(self, doc):
        return doc["text"]

    def doc_to_text(self, doc):
        return doc["query"]

    def doc_to_target(self, doc):
        return doc["answer"]

    def construct_requests(self, doc, ctx):
        return rf.greedy_until(ctx, {"until": None})

    def process_results(self, doc, results):
        raw_output = results[0]
        gold = doc["answer"]

        gpt_input = (
            "你将会收到一段模型的输出内容，这段内容是让模型对文章的犯罪行为，所犯罪名，处罚结果三部分进行提取总结的结果，为了精准地匹配，你需要做的是判断模型有没有提取出内容。如果有，则从中提取模型输出的这三部分内容，如果模型本身就没有总结出来，你就留空，不需要替它总结，严格按照以下格式输出，留空的也需要保持格式：\n"
            "犯罪行为：xxx\n所犯罪名：xxx\n处罚结果：xxx\n\n"
            "注意：对于所犯罪名部分，如果模型没有写'罪'字，你需要帮他补上：\n"
            "模型输出如下：\n"
            f"{raw_output}\n\n"
            "请只返回一个符合上述格式的结果，不要额外解释。"
        )

        client = OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        for _ in range(10):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "你是一个结构化信息抽取助手。"},
                        {"role": "user", "content": gpt_input}
                    ]
                )
                content = response.choices[0].message.content.strip()
                break
            except Exception as e:
                print("GPT请求失败，重试中...", e)
                time.sleep(2)
        else:
            return {
                "score": 0.0,
                "bertscore_crimeact": 0.0,
                "bertscore_punish": 0.0,
                "acc_crime": 0.0,
            }

        def extract_field(pattern, text):
            match = re.search(pattern, text)
            return match.group(1).strip() if match else ""

        pred = {
            "犯罪行为": extract_field(r"犯罪行为[:：](.*)", content),
            "所犯罪名": extract_field(r"所犯罪名[:：](.*)", content),
            "处罚结果": extract_field(r"处罚结果[:：](.*)", content)
        }

        gold_fields = {
            "犯罪行为": extract_field(r"犯罪行为[:：](.*)", gold),
            "所犯罪名": extract_field(r"所犯罪名[:：](.*)", gold),
            "处罚结果": extract_field(r"处罚结果[:：](.*)", gold)
        }

        try:
            bertscore = evaluate.load("src/metrics/bertscore")

            MODEL_TYPE = os.getenv("BERTSCORE_MODEL_TYPE", "hfl/chinese-xlnet-base")
            COMMON_KW = dict(lang="zh", num_layers=5, model_type=MODEL_TYPE)

            bert_result1 = bertscore.compute(
                predictions=[pred["犯罪行为"]],
                references=[gold_fields["犯罪行为"]],
                **COMMON_KW
            )

            bert_result2 = bertscore.compute(
                predictions=[pred["处罚结果"]],
                references=[gold_fields["处罚结果"]],
                **COMMON_KW
            )
            bert_crimeact = bert_result1["f1"][0]
            bert_punish = bert_result2["f1"][0]
        except Exception as e:
            print("BERTScore计算失败", e)
            bert_crimeact = 0.0
            bert_punish = 0.0

        acc_crime = 1.0 if pred["所犯罪名"] == gold_fields["所犯罪名"] else 0.0

        final_score = (bert_crimeact + bert_punish + acc_crime) / 3

        return {
            "score": final_score,
            "bertscore_crimeact": bert_crimeact,
            "bertscore_punish": bert_punish,
            "acc_crime": acc_crime,
        }

    def higher_is_better(self):
        return {
            "score": True,
            "bertscore_crimeact": True,
            "bertscore_punish": True,
            "acc_crime": True,
        }

    def aggregation(self):
        return {
            "score": mean,
            "bertscore_crimeact": mean,
            "bertscore_punish": mean,
            "acc_crime": mean,
        }


class TaxInspect(CheckCase):
    DATASET_PATH = "DATASET_PATH"


class RiskControl(Task):
    VERSION = 1
    DATASET_NAME = None
    EVAL_LAST_TURN = True

    def reformulate_turn_req(self, req, turn_request, turn):
        return req

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def should_decontaminate(self):
        return True

    def doc_to_decontamination_query(self, doc):
        return doc["text"]

    def doc_to_text(self, doc):
        return doc["query"]

    def doc_to_target(self, doc):
        return doc["answer"]

    def construct_requests(self, doc, ctx):
        return rf.greedy_until(ctx, {"until": None})

    def process_results(self, doc, results):
        raw_output = results[0]
        gold = doc["answer"]

        gpt_input = (
            "你将会收到一段模型的输出内容，这段内容是让模型对文章的面临的风险和风险对应的解决方案两部分进行提取总结的结果，为了精准地匹配，你需要做的是判断模型有没有提取出内容。如果有，则从中提取模型输出的这两部分内容，如果模型本身就没有总结出来，你就留空，不需要替它总结，严格按照以下格式输出，留空的也需要保持格式：\n"
            "面临的风险：xxx\n对应的解决措施：xxx\n\n"
            "模型输出如下：\n"
            f"{raw_output}\n\n"
            "请只返回一个符合上述格式的结果，不要额外解释。"
        )

        client = OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        for _ in range(10):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "你是一个结构化信息抽取助手。"},
                        {"role": "user", "content": gpt_input}
                    ]
                )
                content = response.choices[0].message.content.strip()
                break
            except Exception as e:
                print("GPT请求失败，重试中...", e)
                time.sleep(2)
        else:
            return {
                "bertscore_risk": 0.0,
                "bertscore_measure": 0.0,
            }


        def extract_field(pattern, text):
            match = re.search(pattern, text)
            return match.group(1).strip() if match else ""

        pred = {
            "面临的风险": extract_field(r"面临的风险[:：](.*)", content),
            "对应的解决措施": extract_field(r"对应的解决措施[:：](.*)", content)
        }

        gold_fields = {
            "面临的风险": extract_field(r"面临的风险[:：](.*)", gold),
            "对应的解决措施": extract_field(r"对应的解决措施[:：](.*)", gold)
        }

        try:
            bertscore = evaluate.load("src/metrics/bertscore")
            MODEL_TYPE = os.getenv("BERTSCORE_MODEL_TYPE", "hfl/chinese-xlnet-base")

            bert_result1 = bertscore.compute(
                predictions=[pred["面临的风险"]],
                references=[gold_fields["面临的风险"]],
                lang="zh",
                num_layers=5,
                model_type=MODEL_TYPE,
            )

            bert_result2 = bertscore.compute(
                predictions=[pred["对应的解决措施"]],
                references=[gold_fields["对应的解决措施"]],
                lang="zh",
                num_layers=5,
                model_type=MODEL_TYPE,
            )
            bert_risk = bert_result1["f1"][0]
            bert_measure = bert_result2["f1"][0]
        except Exception as e:
            print("BERTScore计算失败", e)
            bert_risk = 0.0
            bert_measure = 0.0

        final_score = (bert_risk + bert_measure) / 2

        return {
            "score": final_score,
            "bertscore_risk": bert_risk,
            "bertscore_measure": bert_measure,
        }

    def higher_is_better(self):
        return {
            "score": True,
            "bertscore_risk": True,
            "bertscore_measure": True,
        }

    def aggregation(self):
        return {
            "score": mean,
            "bertscore_risk": mean,
            "bertscore_measure": mean,
        }


class TaxRisk(RiskControl):
    DATASET_PATH = "DATASET_PATH"


class ReadComprehens(Task):
    VERSION = 1
    DATASET_NAME = None
    EVAL_LAST_TURN = True

    def reformulate_turn_req(self, req, turn_request, turn):
        return req

    def has_training_docs(self):
        return True

    def has_validation_docs(self):
        return True

    def has_test_docs(self):
        return True

    def training_docs(self):
        return self.dataset["train"]

    def validation_docs(self):
        return self.dataset["validation"]

    def test_docs(self):
        return self.dataset["test"]

    def should_decontaminate(self):
        return True

    def doc_to_decontamination_query(self, doc):
        return doc["text"]

    def doc_to_text(self, doc):
        return doc["query"]

    def construct_requests(self, doc, ctx):
        cont_request = rf.greedy_until(ctx, {"until": None})
        return cont_request

    def doc_to_target(self, doc):
        return doc["answer"]

    def process_results(self, doc, results):
        gold = doc["answer"]

        acc = 1.0 if gold in results[0] else 0.0

        return {
            "acc": acc,
        }

    def higher_is_better(self):
        return {
            "acc": True,
        }

    def aggregation(self):
        return {
            "acc": mean,
        }


class TaxRead(ReadComprehens):
    DATASET_PATH = "DATASET_PATH"