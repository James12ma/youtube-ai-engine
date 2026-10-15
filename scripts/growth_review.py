"""Offline evidence review CLI; never researches silently, posts or publishes."""
import argparse,json
from pathlib import Path
from channel.intelligence import TopicBrief,rank_topics,to_review_queue
from channel.community import Discussion,discover,draft_comments,export_drafts

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--topics',type=Path,required=True);parser.add_argument('--discussions',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    topics=[TopicBrief.model_validate(x) for x in json.loads(args.topics.read_text())]
    discussions=[Discussion.model_validate(x) for x in json.loads(args.discussions.read_text())]
    (args.out/'ranked_topics.json').write_text(json.dumps(rank_topics(topics),indent=2))
    (args.out/'topic_queue.review.json').write_text(to_review_queue(topics).model_dump_json(indent=2))
    candidates=discover(discussions,['AI','SaaS','Apps Script','automation','cybersecurity'])
    export_drafts(args.out/'community_drafts.json',draft_comments(candidates))
    print(json.dumps({'topics':len(topics),'comment_drafts':len(candidates),'posting_enabled':False,'publishing_enabled':False,'paid_calls':0}))

if __name__=='__main__':main()
