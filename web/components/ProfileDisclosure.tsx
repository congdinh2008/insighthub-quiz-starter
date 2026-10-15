import type { RuntimeProfile } from "@/lib/api";

export default function ProfileDisclosure({ profile }: { profile: RuntimeProfile | null }) {
  if (!profile) return <div className="profile-disclosure error">Không đọc được cấu hình AI runtime.</div>;
  return (
    <section className="profile-disclosure" aria-label="Cấu hình và chính sách AI">
      <strong>AI profile: {profile.profile}</strong>
      <span>
        Embedding: {profile.embedding.provider}/{profile.embedding.model} ({profile.embedding.dimension}D)
        {" | "}Reranker: {profile.reranker.provider}{profile.reranker.model ? `/${profile.reranker.model}` : ""}
        {" | "}LLM: {profile.llm.provider}/{profile.llm.model}
      </span>
      <span>{profile.mode === "fixture" ? "Fixture chỉ kiểm tra flow, không đánh giá chất lượng semantic." : profile.disclosure.notice}</span>
      {profile.disclosure.external_data_transfer && <strong className="warning">Dữ liệu sẽ rời máy tới provider. Không dùng dữ liệu bí mật hoặc dữ liệu cá nhân khi policy chưa cho phép.</strong>}
      {profile.disclosure.policy_url && <a href={profile.disclosure.policy_url} target="_blank" rel="noreferrer">Chính sách dữ liệu của provider</a>}
    </section>
  );
}
