import { useNavigate } from 'react-router-dom'
import type { FormEvent } from 'react'

export default function EditProfile() {
  const navigate = useNavigate()
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    navigate('/mypage')
  }
  return (
    <section className="mx-auto max-w-2xl">
      <p className="text-sm font-semibold text-blue-600">마이페이지</p>
      <h1 className="mt-2 text-3xl font-black">내 정보 수정</h1>
      <form
        onSubmit={submit}
        className="mt-6 space-y-5 rounded-xl border border-gray-200 bg-white p-6"
      >
        <label className="block text-sm font-semibold">
          생년월일
          <input
            defaultValue="2000.03.24"
            className="mt-2 w-full rounded-lg border border-gray-300 p-3 font-normal"
          />
        </label>
        <label className="block text-sm font-semibold">
          거주지역
          <select
            defaultValue="서울특별시"
            className="mt-2 w-full rounded-lg border border-gray-300 p-3 font-normal"
          >
            <option>서울특별시</option>
            <option>경기도</option>
            <option>인천광역시</option>
          </select>
        </label>
        <label className="block text-sm font-semibold">
          월 소득
          <input
            defaultValue="220"
            type="number"
            className="mt-2 w-full rounded-lg border border-gray-300 p-3 font-normal"
          />
        </label>
        <label className="block text-sm font-semibold">
          주거형태
          <select
            defaultValue="월세"
            className="mt-2 w-full rounded-lg border border-gray-300 p-3 font-normal"
          >
            <option>월세</option>
            <option>전세</option>
            <option>자가</option>
          </select>
        </label>
        <button className="w-full rounded-lg bg-blue-600 py-3.5 font-bold text-white">
          저장하기
        </button>
      </form>
    </section>
  )
}
